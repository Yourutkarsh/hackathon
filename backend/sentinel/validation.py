"""Deterministic structural validation for Sentinel Shift events.

Rules (Phase 1 data contract):
  * Malformed events are QUARANTINED (stored, excluded from trusted processing):
      - INVALID_TIMESTAMP      : timestamp cannot be normalized to UTC.
      - NEGATIVE_VOLUME        : data_mb or file_count present and < 0.
      - INVALID_REQUIRED_TYPE  : a required field is missing or the wrong type.
  * Incomplete-but-valid events are RETAINED and evaluated partially. Missing
    optional components are listed explicitly so downstream confidence penalties
    are deterministic.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Required fields that MUST be present and of type ``str``.
REQUIRED_STR_FIELDS = ("event_id", "user_id", "event_type", "resource_family")
# Optional components whose absence makes an event "incomplete" (still trusted).
OPTIONAL_COMPONENTS = ("user_timezone", "data_mb", "file_count", "sensitivity")

VALID_SENSITIVITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def normalize_timestamp(ts_str: Any, tz_name: Optional[str]) -> Optional[datetime]:
    """Normalize a raw timestamp string to a timezone-aware UTC datetime.

    Absolute strings (``Z`` / explicit offset) are converted directly. Naive
    wall-clock strings require ``tz_name`` to localize. Returns ``None`` when the
    value cannot be normalized (-> INVALID_TIMESTAMP).
    """
    if not isinstance(ts_str, str) or not ts_str.strip():
        return None
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc)
    # Naive wall-clock -> needs a timezone to be absolute.
    if not tz_name:
        return None
    try:
        return dt.replace(tzinfo=ZoneInfo(str(tz_name))).astimezone(timezone.utc)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Validate + normalize a single raw event into a persisted event document.

    Returns a dict with normalized ``timestamp_utc`` and trust flags
    (``quarantined``, ``quarantine_reasons``, ``incomplete``, ``missing_components``).
    """
    reasons: List[str] = []

    # --- required-field type checks ---
    for field in REQUIRED_STR_FIELDS:
        value = raw.get(field)
        if not isinstance(value, str) or not value:
            reasons.append("INVALID_REQUIRED_TYPE")
            break

    # --- volume sanity (negative or non-numeric) ---
    for vol_field in ("data_mb", "file_count"):
        if vol_field in raw and raw[vol_field] is not None:
            v = raw[vol_field]
            if not _is_number(v):
                if "INVALID_REQUIRED_TYPE" not in reasons:
                    reasons.append("INVALID_REQUIRED_TYPE")
            elif v < 0:
                reasons.append("NEGATIVE_VOLUME")

    # --- timestamp normalization ---
    tz_name = raw.get("user_timezone")
    ts_utc = normalize_timestamp(raw.get("timestamp_original"), tz_name)
    if ts_utc is None:
        reasons.append("INVALID_TIMESTAMP")

    quarantined = len(reasons) > 0

    # --- incomplete detection (only meaningful for otherwise-trusted events) ---
    missing: List[str] = []
    if not quarantined:
        for comp in OPTIONAL_COMPONENTS:
            if raw.get(comp) is None:
                missing.append(comp)
        sensitivity = raw.get("sensitivity")
        if sensitivity is not None and str(sensitivity).upper() not in VALID_SENSITIVITIES:
            # Unknown sensitivity value -> treat that component as unavailable.
            if "sensitivity" not in missing:
                missing.append("sensitivity")

    doc: Dict[str, Any] = {
        "event_id": raw.get("event_id"),
        "user_id": raw.get("user_id"),
        "timestamp_original": raw.get("timestamp_original"),
        "timestamp_utc": ts_utc,
        "user_timezone": tz_name,
        "location": raw.get("location"),
        "event_type": raw.get("event_type"),
        "resource_family": raw.get("resource_family"),
        "sensitivity": raw.get("sensitivity"),
        "data_mb": raw.get("data_mb"),
        "file_count": raw.get("file_count"),
        "signals": dict(raw.get("signals") or {}),
        "quarantined": quarantined,
        "quarantine_reasons": sorted(set(reasons)),
        "incomplete": (not quarantined) and len(missing) > 0,
        "missing_components": sorted(missing),
    }
    return doc


def sort_key(doc: Dict[str, Any]) -> Tuple[str, str, str]:
    """Deterministic (timestamp_utc, user_id, event_id) tie-breaking key.

    Quarantined events (timestamp_utc is None) sort first using an empty string,
    keeping the ordering total and reproducible.
    """
    ts = doc.get("timestamp_utc")
    ts_str = ts.isoformat() if isinstance(ts, datetime) else ""
    return (ts_str, str(doc.get("user_id") or ""), str(doc.get("event_id") or ""))

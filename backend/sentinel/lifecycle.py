"""Compliance policy: detection thresholds + baseline lifecycle (V5.1 hardening).

Single source of truth for two policy surfaces that the risk engine itself does
NOT express (the engine stays byte-for-byte immutable):

  * Detection thresholds. The compliance addendum mandates **strict spec
    detection at HIGH/CRITICAL (score >= 70)**. The pre-existing ELEVATED-based
    (score >= 50) detection is retained as a backward-compatible legacy alias so
    current API consumers keep working during migration. Neither threshold is
    ever fed back into the engine; they only classify the engine's own severity.

  * Baseline lifecycle. Exact, testable COLD/WARMING/READY boundaries derived
    from a user's trusted history size and distinct-activity-day count. The
    demo-wide ``baseline_version`` (persisted in ``demo_state``) increments on
    every reset so the UI can prove a reset actually happened.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence

# --------------------------------------------------------------------------- #
# Detection thresholds                                                        #
# --------------------------------------------------------------------------- #
# Strict spec detection (adopted default): HIGH/CRITICAL only.
SPEC_DETECTION_THRESHOLD = 70.0
SPEC_DETECTION_SEVERITIES = ("HIGH", "CRITICAL")
# Legacy/backward-compatible detection: ELEVATED and above.
LEGACY_DETECTION_THRESHOLD = 50.0
LEGACY_DETECTION_SEVERITIES = ("ELEVATED", "HIGH", "CRITICAL")

# Alerting keeps the legacy ELEVATED band so the flagship compound anomaly
# (Rahul E6 = ELEVATED) still surfaces while strict spec detection is adopted
# for evaluation reporting.
FLAGGED_SEVERITIES = frozenset(LEGACY_DETECTION_SEVERITIES)
SPEC_SEVERITIES = frozenset(SPEC_DETECTION_SEVERITIES)


def detection_config() -> Dict[str, Any]:
    """Machine-readable description of the active detection policy."""
    return {
        "adopted": {
            "threshold": SPEC_DETECTION_THRESHOLD,
            "severities": list(SPEC_DETECTION_SEVERITIES),
            "label": "severity >= HIGH (70+)",
            "source": "compliance-addendum",
        },
        "legacy": {
            "threshold": LEGACY_DETECTION_THRESHOLD,
            "severities": list(LEGACY_DETECTION_SEVERITIES),
            "label": "severity >= ELEVATED (50+)",
            "alias_of": "pre-V5.1 detection",
        },
        "alerting_severities": sorted(FLAGGED_SEVERITIES),
        "note": (
            "Strict spec detection (HIGH/CRITICAL, 70+) is the adopted default for "
            "evaluation; ELEVATED-based detection is retained as a legacy alias. "
            "Thresholds never modify engine output."
        ),
    }


# --------------------------------------------------------------------------- #
# Baseline lifecycle                                                          #
# --------------------------------------------------------------------------- #
BASELINE_COLD_BELOW_EVENTS = 20   # < 20 trusted events           -> COLD
BASELINE_READY_MIN_EVENTS = 50    # >= 50 trusted events ...
BASELINE_READY_MIN_DAYS = 7       # ... AND >= 7 distinct days    -> READY
BASELINE_WARMING = "WARMING"
BASELINE_COLD = "COLD"
BASELINE_READY = "READY"
BASELINE_STATES = (BASELINE_COLD, BASELINE_WARMING, BASELINE_READY)


def baseline_state(event_count: int, distinct_days: int) -> str:
    """Exact lifecycle boundary function.

    COLD     : event_count < 20
    WARMING  : 20 <= event_count < 50, or >= 50 events but < 7 distinct days
    READY    : event_count >= 50 AND distinct_days >= 7
    """
    event_count = max(0, int(event_count or 0))
    distinct_days = max(0, int(distinct_days or 0))
    if event_count < BASELINE_COLD_BELOW_EVENTS:
        return BASELINE_COLD
    if event_count < BASELINE_READY_MIN_EVENTS or distinct_days < BASELINE_READY_MIN_DAYS:
        return BASELINE_WARMING
    return BASELINE_READY


def _distinct_days(events: Sequence[Mapping[str, Any]]) -> int:
    days = set()
    for e in events:
        ts = e.get("timestamp_utc")
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            days.add(ts.astimezone(timezone.utc).date().isoformat())
        elif isinstance(ts, str) and ts:
            days.add(ts[:10])
    return len(days)


def baseline_lifecycle(
    events: Sequence[Mapping[str, Any]],
    *,
    baseline_version: Optional[int] = None,
) -> Dict[str, Any]:
    """Describe a user's baseline lifecycle from their trusted events."""
    event_count = len(events)
    distinct_days = _distinct_days(events)
    state = baseline_state(event_count, distinct_days)
    reasons: List[str] = []
    if event_count < BASELINE_COLD_BELOW_EVENTS:
        reasons.append(
            f"needs >= {BASELINE_COLD_BELOW_EVENTS} trusted events (has {event_count})"
        )
    else:
        if event_count < BASELINE_READY_MIN_EVENTS:
            reasons.append(
                f"needs >= {BASELINE_READY_MIN_EVENTS} trusted events (has {event_count})"
            )
        if distinct_days < BASELINE_READY_MIN_DAYS:
            reasons.append(
                f"needs >= {BASELINE_READY_MIN_DAYS} distinct days (has {distinct_days})"
            )
    return {
        "state": state,
        "event_count": event_count,
        "distinct_days": distinct_days,
        "baseline_version": baseline_version,
        "thresholds": {
            "cold_below_events": BASELINE_COLD_BELOW_EVENTS,
            "ready_min_events": BASELINE_READY_MIN_EVENTS,
            "ready_min_days": BASELINE_READY_MIN_DAYS,
        },
        "readiness_reasons": reasons,
    }


__all__ = [
    "SPEC_DETECTION_THRESHOLD",
    "SPEC_DETECTION_SEVERITIES",
    "LEGACY_DETECTION_THRESHOLD",
    "LEGACY_DETECTION_SEVERITIES",
    "FLAGGED_SEVERITIES",
    "SPEC_SEVERITIES",
    "detection_config",
    "BASELINE_COLD",
    "BASELINE_WARMING",
    "BASELINE_READY",
    "BASELINE_STATES",
    "BASELINE_COLD_BELOW_EVENTS",
    "BASELINE_READY_MIN_EVENTS",
    "BASELINE_READY_MIN_DAYS",
    "baseline_state",
    "baseline_lifecycle",
]

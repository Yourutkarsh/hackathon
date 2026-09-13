"""Immutable, deterministic seed fixtures for Sentinel Shift V5.1.

The fixture is built exactly once at import time and frozen. It contains 10
synthetic users, including ``rahul-006`` whose Event 6 is the canonical London /
02:15 AM compound anomaly contrasted against a Bengaluru baseline.

No randomness is used anywhere: every value is literal or a fixed arithmetic
function of a stable index, so ``fixture_hash()`` is byte-stable across runs.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from .validation import sort_key, validate_event

SEED_VERSION = "5.1.0"
ENGINE_VERSION = "5.1"


# --------------------------------------------------------------------------- #
# Users                                                                        #
# --------------------------------------------------------------------------- #
def _baseline(active_start, active_end, families, data_mb, file_counts, bursts):
    return {
        "active_start_minute": active_start,
        "active_end_minute": active_end,
        "resource_families": families,
        "data_mb_baseline": data_mb,
        "file_count_baseline": file_counts,
        "rolling_30m_count_baseline": bursts,
    }


_RAW_USERS: List[Dict[str, Any]] = [
    {
        "user_id": "aria-001", "display_name": "Aria Fernandes",
        "location": {"city": "Lisbon", "country": "Portugal"},
        "user_timezone": "Europe/Lisbon",
        "baseline": _baseline(540, 1080, ["ENG", "DOCS"], [8, 10, 9, 11], [3, 4, 3, 5], [2, 3, 2]),
    },
    {
        "user_id": "mateo-002", "display_name": "Mateo Rossi",
        "location": {"city": "Milan", "country": "Italy"},
        "user_timezone": "Europe/Rome",
        "baseline": _baseline(510, 1050, ["FINANCE", "DOCS"], [14, 16, 13, 15], [5, 6, 4, 5], [3, 4, 3]),
    },
    {
        "user_id": "lin-003", "display_name": "Lin Wei",
        "location": {"city": "Singapore", "country": "Singapore"},
        "user_timezone": "Asia/Singapore",
        "baseline": _baseline(540, 1140, ["ENG", "DATA"], [20, 22, 19, 24], [6, 7, 5, 8], [4, 5, 4]),
    },
    {
        "user_id": "sofia-004", "display_name": "Sofia Alvarez",
        "location": {"city": "Madrid", "country": "Spain"},
        "user_timezone": "Europe/Madrid",
        "baseline": _baseline(600, 1140, ["HR", "DOCS"], [6, 7, 5, 8], [2, 3, 2, 4], [1, 2, 2]),
    },
    {
        "user_id": "omar-005", "display_name": "Omar Haddad",
        "location": {"city": "Dubai", "country": "United Arab Emirates"},
        "user_timezone": "Asia/Dubai",
        "baseline": _baseline(480, 1020, ["FINANCE", "DATA"], [18, 20, 17, 21], [5, 6, 5, 7], [3, 4, 3]),
    },
    {
        "user_id": "rahul-006", "display_name": "Rahul Menon",
        "location": {"city": "Bengaluru", "country": "India"},
        "user_timezone": "Asia/Kolkata",
        "baseline": _baseline(
            540, 1140, ["FINANCE", "ENG", "HR"],
            [12, 15, 11, 13, 17, 14, 16], [3, 5, 4, 4, 6, 4, 5], [2, 3, 2, 4, 3, 2],
        ),
    },
    {
        "user_id": "yuki-007", "display_name": "Yuki Tanaka",
        "location": {"city": "Tokyo", "country": "Japan"},
        "user_timezone": "Asia/Tokyo",
        "baseline": _baseline(540, 1080, ["ENG", "DATA"], [9, 11, 10, 12], [3, 4, 3, 5], [2, 3, 2]),
    },
    {
        "user_id": "nadia-008", "display_name": "Nadia Petrova",
        "location": {"city": "Sofia", "country": "Bulgaria"},
        "user_timezone": "Europe/Sofia",
        "baseline": _baseline(540, 1080, ["DOCS", "HR"], [7, 8, 6, 9], [2, 3, 2, 4], [1, 2, 2]),
    },
    {
        "user_id": "diego-009", "display_name": "Diego Santos",
        "location": {"city": "Sao Paulo", "country": "Brazil"},
        "user_timezone": "America/Sao_Paulo",
        "baseline": _baseline(510, 1050, ["FINANCE", "DOCS"], [13, 15, 12, 16], [4, 5, 4, 6], [3, 4, 3]),
    },
    {
        "user_id": "elena-010", "display_name": "Elena Kuznetsova",
        "location": {"city": "Berlin", "country": "Germany"},
        "user_timezone": "Europe/Berlin",
        "baseline": _baseline(540, 1080, ["ENG", "DATA"], [16, 18, 15, 19], [5, 6, 5, 7], [3, 4, 3]),
    },
]

_USERS_BY_ID = {u["user_id"]: u for u in _RAW_USERS}


# --------------------------------------------------------------------------- #
# Events                                                                       #
# --------------------------------------------------------------------------- #
# Rahul's exact Events 1-8. Event 6 is the London / 02:15 AM compound anomaly.
_RAHUL_EVENTS: List[Dict[str, Any]] = [
    {
        "event_id": "rahul-006-e1", "user_id": "rahul-006",
        "timestamp_original": "2024-06-03T09:12:00", "user_timezone": "Asia/Kolkata",
        "location": {"city": "Bengaluru", "country": "India"},
        "event_type": "LOGIN", "resource_family": "FINANCE", "sensitivity": "MEDIUM",
        "data_mb": 12, "file_count": 3, "signals": {},
    },
    {
        "event_id": "rahul-006-e2", "user_id": "rahul-006",
        "timestamp_original": "2024-06-04T10:05:00", "user_timezone": "Asia/Kolkata",
        "location": {"city": "Bengaluru", "country": "India"},
        "event_type": "FILE_ACCESS", "resource_family": "ENG", "sensitivity": "LOW",
        "data_mb": 15, "file_count": 5, "signals": {},
    },
    {
        "event_id": "rahul-006-e3", "user_id": "rahul-006",
        "timestamp_original": "2024-06-05T14:30:00", "user_timezone": "Asia/Kolkata",
        "location": {"city": "Bengaluru", "country": "India"},
        "event_type": "REPORT", "resource_family": "FINANCE", "sensitivity": "MEDIUM",
        "data_mb": 11, "file_count": 4, "signals": {},
    },
    {
        "event_id": "rahul-006-e4", "user_id": "rahul-006",
        "timestamp_original": "2024-06-06T11:20:00", "user_timezone": "Asia/Kolkata",
        "location": {"city": "Bengaluru", "country": "India"},
        "event_type": "FILE_ACCESS", "resource_family": "HR", "sensitivity": "LOW",
        "data_mb": 13, "file_count": 4, "signals": {},
    },
    {
        "event_id": "rahul-006-e5", "user_id": "rahul-006",
        "timestamp_original": "2024-06-07T18:45:00", "user_timezone": "Asia/Kolkata",
        "location": {"city": "Bengaluru", "country": "India"},
        "event_type": "DEPLOY", "resource_family": "ENG", "sensitivity": "LOW",
        "data_mb": 17, "file_count": 6, "signals": {},
    },
    {
        # EVENT 6 - canonical compound anomaly. London, 02:15 local (BST = 01:15 UTC),
        # baseline contrast is Bengaluru: new location + off-hours + volume spike.
        "event_id": "rahul-006-e6", "user_id": "rahul-006",
        "timestamp_original": "2024-06-08T02:15:00", "user_timezone": "Europe/London",
        "location": {"city": "London", "country": "United Kingdom"},
        "event_type": "BULK_EXPORT", "resource_family": "FINANCE", "sensitivity": "HIGH",
        "data_mb": 240, "file_count": 50,
        "signals": {
            "LOCATION_NOVELTY": 92.0,
            "DEVICE_NOVELTY": 80.0,
            "TIME_DEVIATION": 95.0,
            "VOLUME_SPIKE": 88.0,
        },
    },
    {
        "event_id": "rahul-006-e7", "user_id": "rahul-006",
        "timestamp_original": "2024-06-09T09:30:00", "user_timezone": "Asia/Kolkata",
        "location": {"city": "Bengaluru", "country": "India"},
        "event_type": "LOGIN", "resource_family": "FINANCE", "sensitivity": "MEDIUM",
        "data_mb": 14, "file_count": 4, "signals": {},
    },
    {
        "event_id": "rahul-006-e8", "user_id": "rahul-006",
        "timestamp_original": "2024-06-10T10:15:00", "user_timezone": "Asia/Kolkata",
        "location": {"city": "Bengaluru", "country": "India"},
        "event_type": "FILE_ACCESS", "resource_family": "ENG", "sensitivity": "LOW",
        "data_mb": 16, "file_count": 5, "signals": {},
    },
]

# Yuki's events exercise the quarantine and incomplete-but-valid data rules.
_YUKI_EVENTS: List[Dict[str, Any]] = [
    {
        "event_id": "yuki-007-e1", "user_id": "yuki-007",
        "timestamp_original": "2024-06-05T09:30:00", "user_timezone": "Asia/Tokyo",
        "location": {"city": "Tokyo", "country": "Japan"},
        "event_type": "LOGIN", "resource_family": "ENG", "sensitivity": "LOW",
        "data_mb": 10, "file_count": 3, "signals": {},
    },
    {
        # QUARANTINE: invalid timestamp.
        "event_id": "yuki-007-q1", "user_id": "yuki-007",
        "timestamp_original": "not-a-timestamp", "user_timezone": "Asia/Tokyo",
        "location": {"city": "Tokyo", "country": "Japan"},
        "event_type": "FILE_ACCESS", "resource_family": "DATA", "sensitivity": "LOW",
        "data_mb": 11, "file_count": 4, "signals": {},
    },
    {
        # QUARANTINE: negative volume.
        "event_id": "yuki-007-q2", "user_id": "yuki-007",
        "timestamp_original": "2024-06-06T10:00:00", "user_timezone": "Asia/Tokyo",
        "location": {"city": "Tokyo", "country": "Japan"},
        "event_type": "FILE_ACCESS", "resource_family": "DATA", "sensitivity": "LOW",
        "data_mb": -5, "file_count": 4, "signals": {},
    },
    {
        # QUARANTINE: invalid required type (event_type is not a string).
        "event_id": "yuki-007-q3", "user_id": "yuki-007",
        "timestamp_original": "2024-06-06T11:00:00", "user_timezone": "Asia/Tokyo",
        "location": {"city": "Tokyo", "country": "Japan"},
        "event_type": 12345, "resource_family": "DATA", "sensitivity": "LOW",
        "data_mb": 12, "file_count": 4, "signals": {},
    },
    {
        # INCOMPLETE (retained): missing timezone -> local-time signals unavailable.
        # Provenance timestamp is absolute UTC so it can still be normalized.
        "event_id": "yuki-007-i1", "user_id": "yuki-007",
        "timestamp_original": "2024-06-07T05:00:00Z", "user_timezone": None,
        "location": {"city": "Tokyo", "country": "Japan"},
        "event_type": "FILE_ACCESS", "resource_family": "ENG", "sensitivity": "LOW",
        "data_mb": 12, "file_count": 4, "signals": {},
    },
    {
        # INCOMPLETE (retained): missing volume (data_mb).
        "event_id": "yuki-007-i2", "user_id": "yuki-007",
        "timestamp_original": "2024-06-08T09:45:00", "user_timezone": "Asia/Tokyo",
        "location": {"city": "Tokyo", "country": "Japan"},
        "event_type": "REPORT", "resource_family": "ENG", "sensitivity": "LOW",
        "data_mb": None, "file_count": 4, "signals": {},
    },
]


def _loop_user_events() -> List[Dict[str, Any]]:
    """Deterministically build 2 normal events for each non-Rahul/non-Yuki user."""
    events: List[Dict[str, Any]] = []
    loop_ids = ["aria-001", "mateo-002", "lin-003", "sofia-004",
                "omar-005", "nadia-008", "diego-009", "elena-010"]
    for i, uid in enumerate(loop_ids):
        user = _USERS_BY_ID[uid]
        families = user["baseline"]["resource_families"]
        data_ref = user["baseline"]["data_mb_baseline"]
        file_ref = user["baseline"]["file_count_baseline"]
        for j in range(2):
            day = 2 + ((i + j) % 5)          # 2024-06-02 .. 2024-06-06
            hour = 9 + ((i + 2 * j) % 6)     # 09:00 .. 14:00 (inside active band)
            minute = (13 * (i + j)) % 60
            events.append({
                "event_id": f"{uid}-e{j + 1}",
                "user_id": uid,
                "timestamp_original": f"2024-06-{day:02d}T{hour:02d}:{minute:02d}:00",
                "user_timezone": user["user_timezone"],
                "location": dict(user["location"]),
                "event_type": "LOGIN" if j == 0 else "FILE_ACCESS",
                "resource_family": families[j % len(families)],
                "sensitivity": "LOW" if j == 0 else "MEDIUM",
                "data_mb": data_ref[j % len(data_ref)],
                "file_count": file_ref[j % len(file_ref)],
                "signals": {},
            })
    return events


_RAW_EVENTS: List[Dict[str, Any]] = _RAHUL_EVENTS + _YUKI_EVENTS + _loop_user_events()


# --------------------------------------------------------------------------- #
# Contexts                                                                     #
# --------------------------------------------------------------------------- #
_RAW_CONTEXTS: List[Dict[str, Any]] = [
    {
        # Expired BEFORE Rahul's June events: proves time-range enforcement -
        # this must NOT discount the Event 6 anomaly.
        "context_id": "ctx-rahul-travel-may", "user_id": "rahul-006",
        "affected_signal_families": ["LOCATION_NOVELTY"],
        "raw_reduction_points": 40.0, "confidence": "MEDIUM",
        "start_utc": "2024-05-01T00:00:00Z", "end_utc": "2024-05-31T23:59:59Z",
        "reason": "Approved travel window (May) - expired.",
    },
    {
        "context_id": "ctx-elena-maint", "user_id": "elena-010",
        "affected_signal_families": ["VELOCITY_CHANGE"],
        "raw_reduction_points": 30.0, "confidence": "HIGH",
        "start_utc": "2024-06-01T00:00:00Z", "end_utc": None,
        "reason": "Planned data pipeline maintenance.",
    },
]


# --------------------------------------------------------------------------- #
# Fixture assembly (frozen at import)                                          #
# --------------------------------------------------------------------------- #
def _build_users() -> List[Dict[str, Any]]:
    users = []
    for u in _RAW_USERS:
        doc = copy.deepcopy(u)
        doc["created_at"] = datetime.fromisoformat("2024-05-01T00:00:00+00:00")
        users.append(doc)
    return sorted(users, key=lambda d: d["user_id"])


def _build_events() -> List[Dict[str, Any]]:
    validated = [validate_event(e) for e in _RAW_EVENTS]
    return sorted(validated, key=sort_key)


def _build_contexts() -> List[Dict[str, Any]]:
    from .validation import normalize_timestamp
    ctxs = []
    for c in _RAW_CONTEXTS:
        doc = copy.deepcopy(c)
        doc["start_utc"] = normalize_timestamp(c.get("start_utc"), None)
        doc["end_utc"] = normalize_timestamp(c.get("end_utc"), None)
        ctxs.append(doc)
    return sorted(ctxs, key=lambda d: d["context_id"])


def _canonical(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _canonical(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_canonical(v) for v in obj]
    return obj


_FIXTURE: Dict[str, List[Dict[str, Any]]] = {
    "users": _build_users(),
    "events": _build_events(),
    "contexts": _build_contexts(),
}

_FIXTURE_HASH: str = hashlib.sha256(
    json.dumps(_canonical(_FIXTURE), sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()


def get_fixture() -> Dict[str, List[Dict[str, Any]]]:
    """Return a deep copy of the immutable in-memory fixture (safe to mutate)."""
    return copy.deepcopy(_FIXTURE)


def fixture_hash() -> str:
    """Stable SHA-256 hash over users + events + contexts (excludes volatile state)."""
    return _FIXTURE_HASH


def document_counts() -> Dict[str, int]:
    return {
        "users": len(_FIXTURE["users"]),
        "events": len(_FIXTURE["events"]),
        "contexts": len(_FIXTURE["contexts"]),
        "audit_records": 0,
    }


def build_baseline_for(target: Dict[str, Any],
                       events: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Return the STRICTLY-prior, trusted events usable as ``target``'s baseline.

    Enforces the core rule: no current or future event (by the
    (timestamp_utc, user_id, event_id) key) may enter the baseline used for its
    own score. Quarantined events are never eligible.
    """
    pool = events if events is not None else _FIXTURE["events"]
    target_key = sort_key(target)
    out = []
    for e in pool:
        if e.get("quarantined"):
            continue
        if e.get("user_id") != target.get("user_id"):
            continue
        if sort_key(e) < target_key:
            out.append(e)
    return sorted(out, key=sort_key)

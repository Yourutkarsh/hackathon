"""Immutable, deterministic seed fixtures for Sentinel Shift V5.1.

The fixture is built exactly once at import time and frozen. It contains a
synthetic population (>= 50 users) with 30-60 day histories, multiple labelled
scenario types (SUDDEN_COMPROMISE, GRADUAL_INSIDER, LEGITIMATE_TRAVEL,
ROLE_CHANGE, BENIGN_LATE_WORKER, BENIGN) plus ground-truth labels used by the
evaluation endpoint. ``rahul-006`` Event 6 remains the canonical London / 02:15
AM compound anomaly contrasted against a Bengaluru baseline.

No randomness is used: values are literal or a fixed function of a stable hash,
so ``fixture_hash()`` is byte-stable across runs.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .validation import normalize_timestamp, sort_key, validate_event

SEED_VERSION = "5.2.1"
ENGINE_VERSION = "5.1"

FLAGGED = ("ELEVATED", "HIGH", "CRITICAL")


def _h(*parts: Any) -> int:
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16)


CITIES = [
    ("Lisbon", "Portugal", "Europe/Lisbon"),
    ("Milan", "Italy", "Europe/Rome"),
    ("Singapore", "Singapore", "Asia/Singapore"),
    ("Madrid", "Spain", "Europe/Madrid"),
    ("Dubai", "United Arab Emirates", "Asia/Dubai"),
    ("Tokyo", "Japan", "Asia/Tokyo"),
    ("Sofia", "Bulgaria", "Europe/Sofia"),
    ("Sao Paulo", "Brazil", "America/Sao_Paulo"),
    ("Berlin", "Germany", "Europe/Berlin"),
    ("Toronto", "Canada", "America/Toronto"),
    ("Mumbai", "India", "Asia/Kolkata"),
    ("Seoul", "South Korea", "Asia/Seoul"),
    ("Nairobi", "Kenya", "Africa/Nairobi"),
    ("Austin", "United States", "America/Chicago"),
    ("Oslo", "Norway", "Europe/Oslo"),
    ("Dublin", "Ireland", "Europe/Dublin"),
    ("Warsaw", "Poland", "Europe/Warsaw"),
    ("Cape Town", "South Africa", "Africa/Johannesburg"),
]

RESOURCE_FAMILIES = ["ENG", "DOCS", "FINANCE", "HR", "DATA"]

# Realistic analyst names applied to the whole population (Rahul Menon stays fixed).
NAMES = [
    "Oliver Bennett", "Hamza Malik", "Eleanor Hughes", "Ethan Walker", "Tariq Al-Mansoor",
    "Charlotte Davis", "Liam Harrison", "Lucas Miller", "Zara Siddiqui", "Julian Hayes",
    "Farhan Qureshi", "Henry Carter", "Chloe Morgan", "Mason Cooper", "Zayd Siddiqui",
    "Hazel Montgomery", "Alexander Wright", "James Fletcher", "Layla Qureshi", "Sebastian Cross",
    "Omar Farooq", "Emma Collins", "Daniel Brooks", "Rayan Khan", "Noah Sterling",
    "Grace Sterling", "Callum Hughes", "Bilal Hashmi", "Sophia Bennett", "Leo Crawford",
    "Logan Vance", "Samira Khan", "Jasper Cole", "Zain Mustafa", "Evelyn Shaw",
    "Owen Mercer", "Thomas Thorne", "Ayla Al-Fassi", "Caleb Foster", "Imran Sheikh",
    "Isla Jenkins", "Benjamin Reed", "Samuel Davies", "Yasmin Mirza", "Felix Graham",
    "Adil Rahman", "Harper Price", "George Ellis", "Nathan Russell", "Mariam Farooq",
    "Edward Clark", "Samir Mirza", "Violet Campbell", "Connor Reynolds", "Zachary Taylor",
    "Alice Turner", "Arthur Pendelton", "Yusuf Ansari", "Audrey Palmer", "Clara Vance",
]


# --------------------------------------------------------------------------- #
# Canonical scenario users (hand-authored)                                     #
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


# Rahul's exact Events 1-8. Event 6 is the London / 02:15 AM compound anomaly.
_RAHUL_EVENTS: List[Dict[str, Any]] = [
    {"event_id": "rahul-006-e1", "user_id": "rahul-006", "timestamp_original": "2024-06-03T09:12:00",
     "user_timezone": "Asia/Kolkata", "location": {"city": "Bengaluru", "country": "India"},
     "event_type": "LOGIN", "resource_family": "FINANCE", "sensitivity": "MEDIUM",
     "data_mb": 12, "file_count": 3, "signals": {}},
    {"event_id": "rahul-006-e2", "user_id": "rahul-006", "timestamp_original": "2024-06-04T10:05:00",
     "user_timezone": "Asia/Kolkata", "location": {"city": "Bengaluru", "country": "India"},
     "event_type": "FILE_ACCESS", "resource_family": "ENG", "sensitivity": "LOW",
     "data_mb": 15, "file_count": 5, "signals": {}},
    {"event_id": "rahul-006-e3", "user_id": "rahul-006", "timestamp_original": "2024-06-05T14:30:00",
     "user_timezone": "Asia/Kolkata", "location": {"city": "Bengaluru", "country": "India"},
     "event_type": "REPORT", "resource_family": "FINANCE", "sensitivity": "MEDIUM",
     "data_mb": 11, "file_count": 4, "signals": {}},
    {"event_id": "rahul-006-e4", "user_id": "rahul-006", "timestamp_original": "2024-06-06T11:20:00",
     "user_timezone": "Asia/Kolkata", "location": {"city": "Bengaluru", "country": "India"},
     "event_type": "FILE_ACCESS", "resource_family": "HR", "sensitivity": "LOW",
     "data_mb": 13, "file_count": 4, "signals": {}},
    {"event_id": "rahul-006-e5", "user_id": "rahul-006", "timestamp_original": "2024-06-07T18:45:00",
     "user_timezone": "Asia/Kolkata", "location": {"city": "Bengaluru", "country": "India"},
     "event_type": "DEPLOY", "resource_family": "ENG", "sensitivity": "LOW",
     "data_mb": 17, "file_count": 6, "signals": {}},
    {"event_id": "rahul-006-e6", "user_id": "rahul-006", "timestamp_original": "2024-06-08T02:15:00",
     "user_timezone": "Europe/London", "location": {"city": "London", "country": "United Kingdom"},
     "event_type": "BULK_EXPORT", "resource_family": "FINANCE", "sensitivity": "HIGH",
     "data_mb": 240, "file_count": 50,
     "signals": {"LOCATION_NOVELTY": 92.0, "DEVICE_NOVELTY": 80.0,
                 "TIME_DEVIATION": 95.0, "VOLUME_SPIKE": 88.0}},
    {"event_id": "rahul-006-e7", "user_id": "rahul-006", "timestamp_original": "2024-06-09T09:30:00",
     "user_timezone": "Asia/Kolkata", "location": {"city": "Bengaluru", "country": "India"},
     "event_type": "LOGIN", "resource_family": "FINANCE", "sensitivity": "MEDIUM",
     "data_mb": 14, "file_count": 4, "signals": {}},
    {"event_id": "rahul-006-e8", "user_id": "rahul-006", "timestamp_original": "2024-06-10T10:15:00",
     "user_timezone": "Asia/Kolkata", "location": {"city": "Bengaluru", "country": "India"},
     "event_type": "FILE_ACCESS", "resource_family": "ENG", "sensitivity": "LOW",
     "data_mb": 16, "file_count": 5, "signals": {}},
]

# Yuki's events exercise the quarantine and incomplete-but-valid data rules.
_YUKI_EVENTS: List[Dict[str, Any]] = [
    {"event_id": "yuki-007-e1", "user_id": "yuki-007", "timestamp_original": "2024-06-05T09:30:00",
     "user_timezone": "Asia/Tokyo", "location": {"city": "Tokyo", "country": "Japan"},
     "event_type": "LOGIN", "resource_family": "ENG", "sensitivity": "LOW",
     "data_mb": 10, "file_count": 3, "signals": {}},
    {"event_id": "yuki-007-q1", "user_id": "yuki-007", "timestamp_original": "not-a-timestamp",
     "user_timezone": "Asia/Tokyo", "location": {"city": "Tokyo", "country": "Japan"},
     "event_type": "FILE_ACCESS", "resource_family": "DATA", "sensitivity": "LOW",
     "data_mb": 11, "file_count": 4, "signals": {}},
    {"event_id": "yuki-007-q2", "user_id": "yuki-007", "timestamp_original": "2024-06-06T10:00:00",
     "user_timezone": "Asia/Tokyo", "location": {"city": "Tokyo", "country": "Japan"},
     "event_type": "FILE_ACCESS", "resource_family": "DATA", "sensitivity": "LOW",
     "data_mb": -5, "file_count": 4, "signals": {}},
    {"event_id": "yuki-007-q3", "user_id": "yuki-007", "timestamp_original": "2024-06-06T11:00:00",
     "user_timezone": "Asia/Tokyo", "location": {"city": "Tokyo", "country": "Japan"},
     "event_type": 12345, "resource_family": "DATA", "sensitivity": "LOW",
     "data_mb": 12, "file_count": 4, "signals": {}},
    {"event_id": "yuki-007-i1", "user_id": "yuki-007", "timestamp_original": "2024-06-07T05:00:00Z",
     "user_timezone": None, "location": {"city": "Tokyo", "country": "Japan"},
     "event_type": "FILE_ACCESS", "resource_family": "ENG", "sensitivity": "LOW",
     "data_mb": 12, "file_count": 4, "signals": {}},
    {"event_id": "yuki-007-i2", "user_id": "yuki-007", "timestamp_original": "2024-06-08T09:45:00",
     "user_timezone": "Asia/Tokyo", "location": {"city": "Tokyo", "country": "Japan"},
     "event_type": "REPORT", "resource_family": "ENG", "sensitivity": "LOW",
     "data_mb": None, "file_count": 4, "signals": {}},
]


def _gradual_insider():
    """GRADUAL_INSIDER: escalating after-hours -> novel device -> sensitive -> volume -> multi."""
    uid = "gradual-011"
    loc = {"city": "Toronto", "country": "Canada"}
    tz = "America/Toronto"
    ev = [
        {"event_id": f"{uid}-e1", "user_id": uid, "timestamp_original": "2024-05-20T10:15:00",
         "user_timezone": tz, "location": loc, "event_type": "LOGIN",
         "resource_family": "ENG", "sensitivity": "LOW", "data_mb": 12, "file_count": 3, "signals": {}},
        {"event_id": f"{uid}-e2", "user_id": uid, "timestamp_original": "2024-05-23T19:30:00",
         "user_timezone": tz, "location": loc, "event_type": "FILE_ACCESS",
         "resource_family": "ENG", "sensitivity": "LOW", "data_mb": 16, "file_count": 5, "signals": {}},
        {"event_id": f"{uid}-e3", "user_id": uid, "timestamp_original": "2024-05-26T20:15:00",
         "user_timezone": tz, "location": loc, "event_type": "FILE_ACCESS",
         "resource_family": "DOCS", "sensitivity": "LOW", "data_mb": 18, "file_count": 6, "signals": {}},
        {"event_id": f"{uid}-e4", "user_id": uid, "timestamp_original": "2024-05-29T14:05:00",
         "user_timezone": tz, "location": loc, "event_type": "ACCESS", "resource_family": "PAYROLL",
         "sensitivity": "HIGH", "data_mb": 22, "file_count": 7,
         "signals": {"DEVICE_NOVELTY": 78.0, "APPLICATION_NOVELTY": 70.0}},
        {"event_id": f"{uid}-e5", "user_id": uid, "timestamp_original": "2024-06-01T22:40:00",
         "user_timezone": tz, "location": loc, "event_type": "BULK_EXPORT", "resource_family": "PAYROLL",
         "sensitivity": "HIGH", "data_mb": 185, "file_count": 44,
         "signals": {"VOLUME_SPIKE": 85.0, "DEVICE_NOVELTY": 80.0}},
        {"event_id": f"{uid}-e6", "user_id": uid, "timestamp_original": "2024-06-03T23:10:00",
         "user_timezone": tz, "location": loc, "event_type": "BULK_EXPORT", "resource_family": "PAYROLL",
         "sensitivity": "CRITICAL", "data_mb": 230, "file_count": 60,
         "signals": {"LOCATION_NOVELTY": 82.0, "DEVICE_NOVELTY": 84.0,
                     "VOLUME_SPIKE": 88.0, "TIME_DEVIATION": 80.0}},
    ]
    user = {
        "user_id": uid, "display_name": "Kenji Watada", "location": loc, "user_timezone": tz,
        "baseline": _baseline(540, 1080, ["ENG", "DOCS"],
                              [12, 16, 14, 18, 13, 15, 17, 11], [3, 5, 4, 6, 4, 5, 3, 6], [2, 3, 2, 4, 3, 2]),
        "scenario": {"type": "GRADUAL_INSIDER",
                     "malicious_event_ids": [f"{uid}-e3", f"{uid}-e4", f"{uid}-e5", f"{uid}-e6"],
                     "expected_alert": True},
    }
    return user, ev


def _legit_travel():
    """LEGITIMATE_TRAVEL: novel location but covered by an approved, time-valid context."""
    uid = "travel-012"
    home = {"city": "Berlin", "country": "Germany"}
    ev = [
        {"event_id": f"{uid}-e1", "user_id": uid, "timestamp_original": "2024-05-22T09:30:00",
         "user_timezone": "Europe/Berlin", "location": home, "event_type": "LOGIN",
         "resource_family": "DOCS", "sensitivity": "LOW", "data_mb": 9, "file_count": 3, "signals": {}},
        {"event_id": f"{uid}-e2", "user_id": uid, "timestamp_original": "2024-05-25T11:10:00",
         "user_timezone": "Europe/Berlin", "location": home, "event_type": "FILE_ACCESS",
         "resource_family": "DOCS", "sensitivity": "LOW", "data_mb": 11, "file_count": 4, "signals": {}},
        {"event_id": f"{uid}-e3", "user_id": uid, "timestamp_original": "2024-06-02T10:20:00",
         "user_timezone": "Europe/Paris", "location": {"city": "Paris", "country": "France"},
         "event_type": "LOGIN", "resource_family": "DOCS", "sensitivity": "LOW",
         "data_mb": 12, "file_count": 4, "signals": {"LOCATION_NOVELTY": 55.0}},
        {"event_id": f"{uid}-e4", "user_id": uid, "timestamp_original": "2024-06-05T09:50:00",
         "user_timezone": "Europe/Berlin", "location": home, "event_type": "FILE_ACCESS",
         "resource_family": "DOCS", "sensitivity": "LOW", "data_mb": 10, "file_count": 3, "signals": {}},
        {"event_id": f"{uid}-e5", "user_id": uid, "timestamp_original": "2024-06-08T14:15:00",
         "user_timezone": "Europe/Berlin", "location": home, "event_type": "REPORT",
         "resource_family": "DOCS", "sensitivity": "LOW", "data_mb": 13, "file_count": 5, "signals": {}},
    ]
    user = {
        "user_id": uid, "display_name": "Greta Hoffmann",
        "location": home, "user_timezone": "Europe/Berlin",
        "baseline": _baseline(540, 1080, ["DOCS", "HR"],
                              [9, 11, 10, 12, 8, 13, 10, 11], [3, 4, 3, 5, 4, 3, 4, 5], [2, 3, 2, 3, 2, 2]),
        "scenario": {"type": "LEGITIMATE_TRAVEL", "malicious_event_ids": [], "expected_alert": False},
    }
    return user, ev


def _uncovered_travel():
    """LEGITIMATE_TRAVEL with NO filed context: a benign jet-lagged late login that the
    engine legitimately flags -> a realistic FALSE POSITIVE the analyst later dismisses."""
    uid = "travel-015"
    home = {"city": "Oslo", "country": "Norway"}
    ev = [
        {"event_id": f"{uid}-e1", "user_id": uid, "timestamp_original": "2024-05-24T09:20:00",
         "user_timezone": "Europe/Oslo", "location": home, "event_type": "LOGIN",
         "resource_family": "DOCS", "sensitivity": "LOW", "data_mb": 10, "file_count": 3, "signals": {}},
        {"event_id": f"{uid}-e2", "user_id": uid, "timestamp_original": "2024-05-28T13:40:00",
         "user_timezone": "Europe/Oslo", "location": home, "event_type": "FILE_ACCESS",
         "resource_family": "DOCS", "sensitivity": "LOW", "data_mb": 12, "file_count": 4, "signals": {}},
        {"event_id": f"{uid}-e3", "user_id": uid, "timestamp_original": "2024-06-04T23:40:00",
         "user_timezone": "Europe/Paris", "location": {"city": "Paris", "country": "France"},
         "event_type": "FILE_ACCESS", "resource_family": "DOCS", "sensitivity": "LOW",
         "data_mb": 14, "file_count": 5, "signals": {"LOCATION_NOVELTY": 72.0, "DEVICE_NOVELTY": 58.0}},
        {"event_id": f"{uid}-e4", "user_id": uid, "timestamp_original": "2024-06-07T10:05:00",
         "user_timezone": "Europe/Oslo", "location": home, "event_type": "REPORT",
         "resource_family": "DOCS", "sensitivity": "LOW", "data_mb": 11, "file_count": 4, "signals": {}},
        {"event_id": f"{uid}-e5", "user_id": uid, "timestamp_original": "2024-06-10T14:30:00",
         "user_timezone": "Europe/Oslo", "location": home, "event_type": "FILE_ACCESS",
         "resource_family": "DOCS", "sensitivity": "LOW", "data_mb": 13, "file_count": 4, "signals": {}},
    ]
    user = {
        "user_id": uid, "display_name": "Ingrid Solberg",
        "location": home, "user_timezone": "Europe/Oslo",
        "baseline": _baseline(540, 1080, ["DOCS", "HR"],
                              [10, 12, 11, 13, 9, 12, 10, 11], [3, 4, 3, 5, 4, 3, 4, 5], [2, 3, 2, 3, 2, 2]),
        # Benign ground truth: no filed travel context, so this flags as a FALSE POSITIVE.
        "scenario": {"type": "LEGITIMATE_TRAVEL", "malicious_event_ids": [], "expected_alert": False},
    }
    return user, ev


def _benign_late_worker():
    """BENIGN_LATE_WORKER: 02:00 activity is inside this user's night shift band (no off-hours FP)."""
    uid = "night-013"
    loc = {"city": "Sydney", "country": "Australia"}
    tz = "Australia/Sydney"
    ev = []
    for j in range(6):
        day = datetime(2024, 5, 18) + timedelta(days=j * 4)
        hh = 1 + (j % 3)  # 01:00 - 03:00 local, inside 20:00-05:00 band
        ev.append({
            "event_id": f"{uid}-e{j + 1}", "user_id": uid,
            "timestamp_original": f"{day.date().isoformat()}T{hh:02d}:{(j * 11) % 60:02d}:00",
            "user_timezone": tz, "location": loc, "event_type": "MONITOR",
            "resource_family": "DATA", "sensitivity": "LOW",
            "data_mb": 14 + (j % 5), "file_count": 4 + (j % 3), "signals": {},
        })
    user = {
        "user_id": uid, "display_name": "Mara Nguyen", "location": loc, "user_timezone": tz,
        "baseline": _baseline(1200, 300, ["DATA", "ENG"],
                              [14, 16, 13, 18, 15, 12, 17, 14], [4, 5, 4, 6, 4, 5, 3, 6], [2, 3, 2, 4, 3, 2]),
        "scenario": {"type": "BENIGN_LATE_WORKER", "malicious_event_ids": [], "expected_alert": False},
    }
    return user, ev


def _role_change():
    """ROLE_CHANGE: legitimately accesses a new resource family under an approved role context."""
    uid = "role-014"
    loc = {"city": "Dublin", "country": "Ireland"}
    tz = "Europe/Dublin"
    ev = []
    for j in range(6):
        day = datetime(2024, 5, 15) + timedelta(days=j * 5)
        fam = "ADMIN" if j >= 3 else "ENG"
        sig = {"RESOURCE_NOVELTY": 60.0} if j == 3 else {}
        ev.append({
            "event_id": f"{uid}-e{j + 1}", "user_id": uid,
            "timestamp_original": f"{day.date().isoformat()}T{10 + (j % 5):02d}:{(j * 7) % 60:02d}:00",
            "user_timezone": tz, "location": loc, "event_type": "ACCESS",
            "resource_family": fam, "sensitivity": "MEDIUM" if fam == "ADMIN" else "LOW",
            "data_mb": 12 + (j % 6), "file_count": 4 + (j % 3), "signals": sig,
        })
    user = {
        "user_id": uid, "display_name": "Cormac Byrne", "location": loc, "user_timezone": tz,
        "baseline": _baseline(540, 1080, ["ENG", "ADMIN", "DOCS"],
                              [12, 14, 11, 16, 13, 15, 12, 17], [4, 5, 4, 6, 4, 5, 3, 6], [2, 3, 2, 4, 3, 2]),
        "scenario": {"type": "ROLE_CHANGE", "malicious_event_ids": [], "expected_alert": False},
    }
    return user, ev


# --------------------------------------------------------------------------- #
# Benign population generator (deterministic)                                  #
# --------------------------------------------------------------------------- #
_NAMED = [
    ("aria-001", "Aria Fernandes", 0), ("mateo-002", "Mateo Rossi", 1),
    ("lin-003", "Lin Wei", 2), ("sofia-004", "Sofia Alvarez", 3),
    ("omar-005", "Omar Haddad", 4), ("nadia-008", "Nadia Petrova", 6),
    ("diego-009", "Diego Santos", 7), ("elena-010", "Elena Kuznetsova", 8),
]


def _benign_user(uid: str, name: str, city_idx: int):
    city, country, tz = CITIES[city_idx % len(CITIES)]
    uh = _h(uid, "seed")
    base_vol = 8 + (uh % 22)
    data_baseline = [max(1, base_vol + d) for d in (-3, 0, 2, -1, 4, 1, -2, 3)]
    file_baseline = [3, 5, 4, 6, 4, 3, 5, 4]
    k = 5 + (uh % 4)  # 5..8 events
    start = datetime(2024, 5, 1) + timedelta(days=uh % 18)
    events = []
    for j in range(k):
        eh = _h(uid, j, "v")
        day = start + timedelta(days=j * 5 + (uh % 3))
        hour = 8 + (eh % 8)  # 08..15, inside 08:00-18:00 band
        minute = (eh // 7) % 60
        vol = max(1, base_vol + ((eh % 11) - 5))
        files = max(1, 3 + ((eh // 13) % 5))
        events.append({
            "event_id": f"{uid}-e{j + 1}", "user_id": uid,
            "timestamp_original": f"{day.date().isoformat()}T{hour:02d}:{minute:02d}:00",
            "user_timezone": tz, "location": {"city": city, "country": country},
            "event_type": ["LOGIN", "FILE_ACCESS", "REPORT", "ACCESS"][j % 4],
            "resource_family": RESOURCE_FAMILIES[(j + uh) % len(RESOURCE_FAMILIES)],
            "sensitivity": "MEDIUM" if j % 3 == 0 else "LOW",
            "data_mb": vol, "file_count": files, "signals": {},
        })
    user = {
        "user_id": uid, "display_name": name,
        "location": {"city": city, "country": country}, "user_timezone": tz,
        "baseline": _baseline(480, 1080, RESOURCE_FAMILIES[:3],
                              data_baseline, file_baseline, [2, 3, 2, 4, 3, 2]),
        "scenario": {"type": "BENIGN", "malicious_event_ids": [], "expected_alert": False},
    }
    return user, events


def _build_population():
    raw_users: List[Dict[str, Any]] = []
    raw_events: List[Dict[str, Any]] = []

    # Rahul (SUDDEN_COMPROMISE) + Yuki (data-quality demo) keep their exact events.
    raw_users.append({
        "user_id": "rahul-006", "display_name": "Rahul Menon",
        "location": {"city": "Bengaluru", "country": "India"}, "user_timezone": "Asia/Kolkata",
        "baseline": _baseline(540, 1140, ["FINANCE", "ENG", "HR"],
                              [12, 15, 11, 13, 17, 14, 16], [3, 5, 4, 4, 6, 4, 5], [2, 3, 2, 4, 3, 2]),
        "scenario": {"type": "SUDDEN_COMPROMISE", "malicious_event_ids": ["rahul-006-e6"],
                     "expected_alert": True},
    })
    raw_events += _RAHUL_EVENTS
    raw_users.append({
        "user_id": "yuki-007", "display_name": "Yuki Tanaka",
        "location": {"city": "Tokyo", "country": "Japan"}, "user_timezone": "Asia/Tokyo",
        "baseline": _baseline(540, 1080, ["ENG", "DATA"],
                              [9, 11, 10, 12], [3, 4, 3, 5], [2, 3, 2]),
        "scenario": {"type": "BENIGN", "malicious_event_ids": [], "expected_alert": False},
    })
    raw_events += _YUKI_EVENTS

    # Hand-authored scenario users.
    for maker in (_gradual_insider, _legit_travel, _uncovered_travel,
                  _benign_late_worker, _role_change):
        u, ev = maker()
        raw_users.append(u)
        raw_events += ev

    # Named benign users (expanded histories).
    for uid, name, ci in _NAMED:
        u, ev = _benign_user(uid, name, ci)
        raw_users.append(u)
        raw_events += ev

    # Generated benign users to reach a 50-100 population.
    for i in range(15, 61):
        uid = f"user-{i:03d}"
        u, ev = _benign_user(uid, f"Analyst {i:03d}", i)
        raw_users.append(u)
        raw_events += ev

    return raw_users, raw_events


_RAW_USERS, _RAW_EVENTS = _build_population()


_RAW_CONTEXTS: List[Dict[str, Any]] = [
    {"context_id": "ctx-rahul-travel-may", "user_id": "rahul-006",
     "affected_signal_families": ["LOCATION_NOVELTY"], "raw_reduction_points": 40.0,
     "confidence": "MEDIUM", "start_utc": "2024-05-01T00:00:00Z", "end_utc": "2024-05-31T23:59:59Z",
     "reason": "Approved travel window (May) - expired before the June anomaly."},
    {"context_id": "ctx-travel-paris", "user_id": "travel-012",
     "affected_signal_families": ["LOCATION_NOVELTY"], "raw_reduction_points": 60.0,
     "confidence": "HIGH", "start_utc": "2024-06-01T00:00:00Z", "end_utc": "2024-06-04T00:00:00Z",
     "reason": "Approved Paris business trip - time-valid, discounts location novelty."},
    {"context_id": "ctx-role-admin", "user_id": "role-014",
     "affected_signal_families": ["RESOURCE_NOVELTY"], "raw_reduction_points": 55.0,
     "confidence": "HIGH", "start_utc": "2024-05-25T00:00:00Z", "end_utc": None,
     "reason": "Promotion to platform admin - approved new resource access."},
    {"context_id": "ctx-elena-maint", "user_id": "elena-010",
     "affected_signal_families": ["VELOCITY_CHANGE"], "raw_reduction_points": 30.0,
     "confidence": "HIGH", "start_utc": "2024-06-01T00:00:00Z", "end_utc": None,
     "reason": "Planned data pipeline maintenance."},
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
    users.sort(key=lambda d: d["user_id"])
    # Apply the realistic name roster in stable order; Rahul Menon is fixed.
    idx = 0
    for doc in users:
        if doc["user_id"] == "rahul-006":
            doc["display_name"] = "Rahul Menon"
            continue
        doc["display_name"] = NAMES[idx % len(NAMES)]
        idx += 1
    return users


def _build_events() -> List[Dict[str, Any]]:
    validated = [validate_event(e) for e in _RAW_EVENTS]
    return sorted(validated, key=sort_key)


def _build_contexts() -> List[Dict[str, Any]]:
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

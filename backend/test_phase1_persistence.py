"""Phase 1 verification gate for Sentinel Shift V5.1.

Run:  python test_phase1_persistence.py   (from /app/backend)

Verifies: engine integrity/import contract, seed integrity, reset
reproducibility, required collections + compound indexes, deterministic event
ordering, the exact Rahul Event 6 London/02:15 fixture, quarantine and
incomplete-event rules, baseline eligibility, and the warm-reset target.
It also runs the untouched ``test_v51_fixes.py`` and asserts it still passes.
"""
import subprocess
import sys
from datetime import datetime, timezone

import risk_engine_v5_1 as engine
from sentinel import (
    ENGINE_CHECKSUM,
    build_baseline_for,
    ensure_indexes,
    fixture_hash,
    get_db,
    get_fixture,
    reset_demo_db,
    verify_engine_integrity,
)
from sentinel.demo_db import DEMO_COLLECTIONS
from sentinel.validation import sort_key

PASS = "\033[92mPASS\033[0m"


def check(label, condition, detail=""):
    assert condition, f"FAIL: {label} {detail}"
    print(f"  [{PASS}] {label}")


def _as_naive_utc(dt):
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def main():
    db = get_db()

    # --- 1. Immutable engine: checksum + import contract ---------------------
    print("\n1. Immutable engine loading")
    check("engine checksum matches recorded value", verify_engine_integrity(),
          f"(recorded {ENGINE_CHECKSUM[:12]}...)")
    for name in ("rule_detector", "normalized_components", "compute_final_risk_score",
                 "severity_for_score", "confidence_score"):
        check(f"engine exports {name}", name in engine.__all__ and hasattr(engine, name))

    # --- 2. Seed / reset integrity ------------------------------------------
    print("\n2. Seed & reset integrity")
    report1 = reset_demo_db(db)
    state1 = db["demo_state"].find_one({})
    check("demo_state fixture_hash == computed hash", state1["fixture_hash"] == fixture_hash())
    check("engine_checksum persisted in demo_state", state1["engine_checksum"] == ENGINE_CHECKSUM)
    counts = report1["document_counts"]
    check("users count matches fixture (>= 50)",
          db["users"].count_documents({}) == counts["users"] and counts["users"] >= 50,
          f"got {counts['users']}")
    check("events count matches fixture",
          db["events"].count_documents({}) == counts["events"], f"={counts['events']}")
    check("contexts count matches fixture",
          db["contexts"].count_documents({}) == counts["contexts"])
    check("audit_records seeded empty (append-only)", db["audit_records"].count_documents({}) == 0)

    # --- 3. Reset reproducibility -------------------------------------------
    print("\n3. Reset reproducibility (identical hash & counts)")
    report2 = reset_demo_db(db)
    check("fixture_hash stable across resets", report1["fixture_hash"] == report2["fixture_hash"])
    check("document_counts stable across resets",
          report1["document_counts"] == report2["document_counts"])

    # --- 4. Required collections + compound indexes -------------------------
    print("\n4. Collections & compound indexes")
    existing = set(db.list_collection_names())
    for coll in DEMO_COLLECTIONS:
        check(f"collection '{coll}' exists", coll in existing)
    idx = ensure_indexes(db)
    ev_idx = {tuple(i["key"].items()): i["name"] for i in db["events"].list_indexes()}
    compound_key = (("timestamp_utc", 1), ("user_id", 1), ("event_id", 1))
    check("events compound index {timestamp_utc,user_id,event_id} exists", compound_key in ev_idx)
    check("events.user_id index exists", "events_user_id" in idx["events"])
    check("users.user_id index exists", "users_user_id_unique" in idx["users"])
    check("contexts.user_id index exists", "contexts_user_id" in idx["contexts"])
    check("audit lookup indexes exist",
          "audit_user_id" in idx["audit_records"] and "audit_event_id" in idx["audit_records"])

    # --- 5. Deterministic event ordering ------------------------------------
    print("\n5. Event ordering (timestamp_utc, user_id, event_id)")
    db_order = [d["event_id"] for d in db["events"].find(
        {}, {"_id": 0}).sort([("timestamp_utc", 1), ("user_id", 1), ("event_id", 1)])]
    fx_order = [e["event_id"] for e in sorted(get_fixture()["events"], key=sort_key)]
    check("DB compound-sorted order == fixture sort order", db_order == fx_order)

    # --- 6. Rahul Event 6 exact London / 02:15 fixture ----------------------
    print("\n6. Rahul Event 6 compound anomaly")
    e6 = db["events"].find_one({"event_id": "rahul-006-e6"}, {"_id": 0})
    check("E6 city == London", e6["location"]["city"] == "London")
    check("E6 country == United Kingdom", e6["location"]["country"] == "United Kingdom")
    check("E6 timezone == Europe/London", e6["user_timezone"] == "Europe/London")
    ts_utc = _as_naive_utc(e6["timestamp_utc"])
    check("E6 timestamp_utc == 2024-06-08 01:15 UTC", ts_utc == datetime(2024, 6, 8, 1, 15),
          f"got {ts_utc.isoformat()}")
    minute = engine._minute_of_day(ts_utc.replace(tzinfo=timezone.utc).isoformat(), "Europe/London")
    check("E6 local time == 02:15 (minute 135)", minute == 135, f"got {minute}")
    check("E6 provenance string preserved", e6["timestamp_original"] == "2024-06-08T02:15:00")
    check("E6 is trusted (not quarantined)", e6["quarantined"] is False)

    # --- 7. Baseline eligibility (no current/future event) ------------------
    print("\n7. Baseline eligibility rule")
    baseline = build_baseline_for(e6, get_fixture()["events"])
    ids = {b["event_id"] for b in baseline}
    check("E6 not in its own baseline", "rahul-006-e6" not in ids)
    check("baseline is exactly E1..E5", ids == {f"rahul-006-e{i}" for i in range(1, 6)}, str(ids))
    e6_key = sort_key(e6)
    check("every baseline event is strictly prior", all(sort_key(b) < e6_key for b in baseline))

    # --- 8. Quarantine rules -------------------------------------------------
    print("\n8. Quarantine rules")
    q1 = db["events"].find_one({"event_id": "yuki-007-q1"}, {"_id": 0})
    q2 = db["events"].find_one({"event_id": "yuki-007-q2"}, {"_id": 0})
    q3 = db["events"].find_one({"event_id": "yuki-007-q3"}, {"_id": 0})
    check("invalid timestamp -> quarantined INVALID_TIMESTAMP",
          q1["quarantined"] and "INVALID_TIMESTAMP" in q1["quarantine_reasons"])
    check("negative volume -> quarantined NEGATIVE_VOLUME",
          q2["quarantined"] and "NEGATIVE_VOLUME" in q2["quarantine_reasons"])
    check("invalid required type -> quarantined INVALID_REQUIRED_TYPE",
          q3["quarantined"] and "INVALID_REQUIRED_TYPE" in q3["quarantine_reasons"])
    trusted = db["events"].count_documents({"quarantined": False})
    quarantined = db["events"].count_documents({"quarantined": True})
    check("quarantined events excluded from trusted set", quarantined == 3 and trusted >= 1,
          f"trusted={trusted} quarantined={quarantined}")

    # --- 9. Incomplete-but-valid rules --------------------------------------
    print("\n9. Incomplete-event rules")
    i1 = db["events"].find_one({"event_id": "yuki-007-i1"}, {"_id": 0})
    i2 = db["events"].find_one({"event_id": "yuki-007-i2"}, {"_id": 0})
    check("missing-timezone event retained (not quarantined)", i1["quarantined"] is False)
    check("missing-timezone marked incomplete w/ user_timezone",
          i1["incomplete"] and "user_timezone" in i1["missing_components"])
    check("missing-volume event retained + incomplete",
          i2["quarantined"] is False and i2["incomplete"] and "data_mb" in i2["missing_components"])
    conf_full = engine.confidence_score(baseline_ready=True, timezone_available=True,
                                        iforest_available=True, sensitivity_history_available=True,
                                        required_missing_fraction=0.0)
    conf_no_tz = engine.confidence_score(baseline_ready=True, timezone_available=False,
                                         iforest_available=True, sensitivity_history_available=True,
                                         required_missing_fraction=0.0)
    check("missing-timezone deterministically lowers confidence (100 -> 90)",
          conf_full == 100 and conf_no_tz == 90, f"{conf_full}/{conf_no_tz}")

    # --- 10. Warm reset performance target (warn-only) ----------------------
    print("\n10. Reset performance (warm target)")
    r = reset_demo_db(db)
    if r["performance_ok"]:
        check(f"reset {r['reset_duration_ms']} ms <= {r['reset_target_ms']} ms", True)
    else:
        print(f"  [\033[93mWARN\033[0m] {r['performance_warning']}")

    # --- 11. Untouched targeted engine tests still pass ---------------------
    print("\n11. test_v51_fixes.py (must pass unchanged)")
    proc = subprocess.run([sys.executable, "test_v51_fixes.py"], capture_output=True, text=True)
    check("test_v51_fixes.py passes unchanged",
          proc.returncode == 0 and "ALL_TARGETED_TESTS_PASSED" in proc.stdout,
          proc.stdout + proc.stderr)

    print("\n\033[92mPHASE 1 VERIFICATION GATE: ALL CHECKS PASSED\033[0m")


if __name__ == "__main__":
    main()

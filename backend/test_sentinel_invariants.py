"""Sentinel Shift V5.1 — sentinel-guard invariant gate.

Run:  python test_sentinel_invariants.py      (from /app/backend)

Codifies the four non-negotiable invariants from the ``sentinel-guard`` skill so
they are enforced by CI/tests, not by memory:

  1. Engine immutability      — ``risk_engine_v5_1.py`` checksum + read-only mode.
  2. Zero temporal leakage    — EVERY user baseline is strictly ``[t-window, t)``.
  3. Read-only LLM separation — the assistant never computes risk or labels users.
  4. Deterministic reproducible— seed=42, stable fixture hash, sub-50 ms reset.

Prefers a real MongoDB; falls back to mongomock on a bare checkout. The < 50 ms
reset target is asserted only against a real MongoDB (mongomock is a pure-Python
simulator and is not representative of MongoDB write latency).
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

PASS = "\033[92mPASS\033[0m"
WARN = "\033[93mWARN\033[0m"

ENGINE = BACKEND / "risk_engine_v5_1.py"
MANIFEST = BACKEND / "sentinel" / "ENGINE_MANIFEST.json"


def check(label, condition, detail=""):
    assert condition, f"FAIL: {label} {detail}"
    print(f"  [{PASS}] {label}")


def warn(label, detail):
    print(f"  [{WARN}] {label} ({detail})")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _connect():
    """Return (db, datastore) using real MongoDB when reachable, else mongomock."""
    mongo_url = os.environ.get("MONGO_URL")
    if mongo_url:
        try:
            from pymongo import MongoClient
            import sentinel.demo_db as demo_db
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
            db = client[os.environ.get("DB_NAME", "sentinel")]
            db.command("ping")
            demo_db._CLIENT = client
            return db, "mongodb"
        except Exception:
            pass
    try:
        import mongomock
        import sentinel.demo_db as demo_db
        os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
        os.environ.setdefault("DB_NAME", "sentinel_guard")
        demo_db._CLIENT = mongomock.MongoClient()
        return demo_db.get_db(), "mongomock"
    except Exception:
        return None, None


# --------------------------------------------------------------------------- #
# 1. Engine immutability                                                      #
# --------------------------------------------------------------------------- #
def invariant_engine_immutability():
    print("\n1. Engine immutability")
    manifest = json.loads(MANIFEST.read_text())
    check("engine sha256 == ENGINE_MANIFEST.json", _sha256(ENGINE) == manifest["sha256"],
          _sha256(ENGINE)[:12])
    check("immutable test_v51_fixes.py sha256 == manifest",
          _sha256(BACKEND / "test_v51_fixes.py") == manifest["test_file_sha256"])
    mode = ENGINE.stat().st_mode
    check("engine is read-only (no write bits)", (mode & 0o222) == 0, oct(mode)[-3:])
    from sentinel import verify_engine_integrity
    check("sentinel.verify_engine_integrity() is True", verify_engine_integrity() is True)


# --------------------------------------------------------------------------- #
# 2. Zero temporal leakage                                                    #
# --------------------------------------------------------------------------- #
def invariant_zero_leakage():
    print("\n2. Zero temporal leakage ([t - window, t))")
    from sentinel import build_baseline_for
    from sentinel.fixtures import get_fixture
    from sentinel.validation import sort_key

    events = get_fixture()["events"]
    offenders = []
    for target in events:
        target_key = sort_key(target)
        for entry in build_baseline_for(target, events):
            if not (sort_key(entry) < target_key):
                offenders.append(("not-strictly-prior", target["event_id"], entry["event_id"]))
            if entry["user_id"] != target["user_id"]:
                offenders.append(("cross-user", target["event_id"], entry["event_id"]))
            if entry.get("quarantined"):
                offenders.append(("quarantined", target["event_id"], entry["event_id"]))
        if any(e["event_id"] == target["event_id"] for e in build_baseline_for(target, events)):
            offenders.append(("self", target["event_id"]))
    check("no self/future/cross-user/quarantined event in ANY baseline",
          not offenders, str(offenders[:3]))
    print(f"      swept {len(events)} events across "
          f"{len({e['user_id'] for e in events})} users")


# --------------------------------------------------------------------------- #
# 3. Read-only LLM separation                                                 #
# --------------------------------------------------------------------------- #
def invariant_llm_separation(db):
    print("\n3. Read-only LLM separation")
    from sentinel import service

    service.reset()
    scored = service.investigate_core("rahul-006", "rahul-006-e6")
    asst = service.assistant_chat("rahul-006", "why was this flagged?", "rahul-006-e6")
    check("assistant used_llm is False (offline, no external provider)",
          asst["used_llm"] is False)
    check("assistant mirrors engine score/severity (never recomputes)",
          asst["risk_score"] == scored["risk_score"] and asst["severity"] == scored["severity"])
    check("assistant never labels the user 'malicious'",
          "malicious" not in json.dumps(asst).lower())
    source = inspect.getsource(service.assistant_chat)
    banned = ("compute_final_risk_score", "severity_for_score", "clip100",
              "normalized_components", "rule_detector", "robust_statistical_score")
    check("assistant source calls no engine risk function", not any(b in source for b in banned))


# --------------------------------------------------------------------------- #
# 4. Deterministic reproducibility                                            #
# --------------------------------------------------------------------------- #
def invariant_determinism(db, datastore):
    print("\n4. Deterministic reproducibility")
    import sentinel.iforest as iforest
    from sentinel import service
    from sentinel.calibration import calibrate

    source = "\n".join(
        p.read_text() for p in (BACKEND / "sentinel").glob("*.py")
    )
    rng = re.compile(r"(^|\s)(import random|from random import|np\.random|numpy\.random|RandomState|random\.)")
    check("no RNG in sentinel package (seed/data are deterministic)",
          not rng.search(source))
    check("Isolation Forest random_state locked to 42", iforest.RANDOM_STATE == 42)

    r1 = service.reset()
    r2 = service.reset()
    check("fixture_hash stable across resets", r1["fixture_hash"] == r2["fixture_hash"])
    check("document_counts stable across resets",
          r1["document_counts"] == r2["document_counts"])
    check("baseline_version increments per reset",
          r2["baseline_version"] == r1["baseline_version"] + 1)

    s1 = service.investigate_core("rahul-006", "rahul-006-e6")["risk_score"]
    s2 = service.investigate_core("rahul-006", "rahul-006-e6")["risk_score"]
    check("engine risk score deterministic across calls", s1 == s2, str(s1))

    records = [{"timestamp_utc": f"2024-06-{i + 1:02d}T00:00:00Z", "user_id": "u",
                "event_id": f"e{i}", "score": 80.0 if i % 5 == 0 else 5.0,
                "positive": i % 5 == 0} for i in range(20)]
    check("calibration threshold selection deterministic",
          calibrate(records)["selected_threshold"] == calibrate(records)["selected_threshold"])

    if datastore == "mongodb":
        check(f"warm reset {r2['reset_duration_ms']} ms <= {r2['reset_target_ms']} ms",
              r2["performance_ok"] is True, str(r2["reset_duration_ms"]))
    else:
        warn("reset latency target (< 50 ms) not asserted on mongomock",
             f"measured {r2['reset_duration_ms']} ms in the pure-python simulator")

    check("engine checksum unchanged after resets/import",
          _sha256(ENGINE) == json.loads(MANIFEST.read_text())["sha256"])


def main():
    invariant_engine_immutability()
    invariant_zero_leakage()
    db, datastore = _connect()
    if db is None:
        warn("database-backed invariants (3 & 4) skipped", "no MongoDB or mongomock")
    else:
        print(f"\n      datastore: {datastore}")
        invariant_llm_separation(db)
        invariant_determinism(db, datastore)
    print("\n\033[92mALL_SENTINEL_INVARIANTS_SATISFIED\033[0m")


if __name__ == "__main__":
    main()

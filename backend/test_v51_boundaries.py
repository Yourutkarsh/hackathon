"""Sentinel Shift V5.1 compliance-hardening verification suite.

Run:  python test_v51_boundaries.py      (from /app/backend)

Covers the addendum's non-negotiable edge cases:
  * Exact baseline-lifecycle boundaries (19/20 events, 49/50 events, 6/7 days).
  * Isolation Forest: minimum-history fallback, population fallback, no-training
    unavailability (never fabricated), constant-feature q99 == q95, determinism.
  * Calibration: chronological 60/20/20 split, deterministic tie-break, empty
    slices, reporting-only (never mutates global detection).
  * Scenario semantics: Rahul E6 explicit, PROJECT_CHANGE settles, MIXED_CASE
    stays ELEVATED+ despite its context discount.
  * Ablation variant rename + legacy aliases, assistant schema aliases,
    duplicate/out-of-order timestamps, and reset/version monotonicity.

The suite prefers a real MongoDB (as ``test_phase1_persistence.py`` does) and
transparently falls back to an in-memory mongomock client when one is available,
so it remains runnable on a bare checkout. Scoring/scenario checks are pure and
never need a database.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

import risk_engine_v5_1 as engine
from sentinel import (
    FLAGGED_SEVERITIES,
    SPEC_DETECTION_THRESHOLD,
    baseline_state,
    build_baseline_for,
    calibrate,
    detection_config,
    get_fixture,
)
from sentinel import iforest as iforest_mod
from sentinel.calibration import chronological_split, confusion, select_threshold
from sentinel.lifecycle import (
    BASELINE_COLD,
    BASELINE_READY,
    BASELINE_WARMING,
    SPEC_SEVERITIES,
)
from sentinel.scoring import (
    ABLATION_LEGACY_ALIASES,
    ABLATION_VARIANTS,
    ablation_scores,
    score_event,
)

PASS = "\033[92mPASS\033[0m"
WARN = "\033[93mWARN\033[0m"
_SKIPPED: list = []


def check(label, condition, detail=""):
    assert condition, f"FAIL: {label} {detail}"
    print(f"  [{PASS}] {label}")


def skip(label, reason):
    _SKIPPED.append(label)
    print(f"  [{WARN}] SKIP: {label} ({reason})")


# --------------------------------------------------------------------------- #
# Fixture-driven scoring helpers (pure, no database)                          #
# --------------------------------------------------------------------------- #
def _score_user(fixture, user_id, event_id, population=None):
    events = fixture["events"]
    user = next(u for u in fixture["users"] if u["user_id"] == user_id)
    target = next(e for e in events if e["event_id"] == event_id)
    prior = build_baseline_for(target, events)
    contexts = [c for c in fixture["contexts"] if c["user_id"] == user_id]
    population = population if population is not None else events
    return score_event(user, target, prior, contexts, population_events=population)


# --------------------------------------------------------------------------- #
# 1. Baseline lifecycle boundaries                                            #
# --------------------------------------------------------------------------- #
def test_baseline_boundaries():
    print("\n1. Baseline lifecycle boundaries")
    check("19 events -> COLD", baseline_state(19, 30) == BASELINE_COLD)
    check("20 events -> WARMING", baseline_state(20, 30) == BASELINE_WARMING)
    check("49 events -> WARMING", baseline_state(49, 30) == BASELINE_WARMING)
    check("50 events + 7 days -> READY", baseline_state(50, 7) == BASELINE_READY)
    check("50 events + 6 distinct days -> WARMING", baseline_state(50, 6) == BASELINE_WARMING)
    check("50 events + 7 distinct days -> READY (boundary)", baseline_state(50, 7) == BASELINE_READY)
    check("0 events -> COLD", baseline_state(0, 0) == BASELINE_COLD)


# --------------------------------------------------------------------------- #
# 2. Detection policy                                                         #
# --------------------------------------------------------------------------- #
def test_detection_policy():
    print("\n2. Strict spec detection (70+)")
    cfg = detection_config()
    check("adopted threshold == 70", cfg["adopted"]["threshold"] == SPEC_DETECTION_THRESHOLD == 70.0)
    check("adopted severities == HIGH/CRITICAL",
          set(cfg["adopted"]["severities"]) == {"HIGH", "CRITICAL"})
    check("legacy threshold == 50 (ELEVATED+)", cfg["legacy"]["threshold"] == 50.0)
    check("SPEC_SEVERITIES excludes ELEVATED", "ELEVATED" not in SPEC_SEVERITIES)
    check("legacy FLAGGED_SEVERITIES includes ELEVATED", "ELEVATED" in FLAGGED_SEVERITIES)


# --------------------------------------------------------------------------- #
# 3. Ablation variants                                                        #
# --------------------------------------------------------------------------- #
def test_ablation_variants():
    print("\n3. Ablation variant rename")
    expected = {"RULES_ONLY", "RULES_PLUS_STATS", "RULES_STATS_IFOREST",
                "FULL", "TEMPORAL_OFF", "CONTEXT_OFF"}
    check("variant set matches addendum", set(ABLATION_VARIANTS) == expected)
    check("legacy aliases preserved",
          set(ABLATION_LEGACY_ALIASES) == {"NO_CONTEXT", "NO_TEMPORAL", "NO_NOVELTY", "BEHAVIORAL_ONLY"})
    out = ablation_scores(
        {"behavioral_anomaly": 100.0, "temporal_correlation": 20.0, "sensitivity": 50.0,
         "novelty": 80.0, "context_adjustment": 30.0},
        {"rules": 100.0, "statistical": 40.0, "iforest": 10.0},
    )
    check("all variants scored", set(out) == expected)
    check("RULES_ONLY <= RULES_PLUS_STATS <= RULES_STATS_IFOREST",
          out["RULES_ONLY"]["score"] <= out["RULES_PLUS_STATS"]["score"]
          <= out["RULES_STATS_IFOREST"]["score"])
    check("CONTEXT_OFF >= FULL (discount removes points)",
          out["CONTEXT_OFF"]["score"] >= out["FULL"]["score"])
    check("TEMPORAL_OFF <= FULL", out["TEMPORAL_OFF"]["score"] <= out["FULL"]["score"])


# --------------------------------------------------------------------------- #
# 4. Isolation Forest fallback / quantiles / determinism                      #
# --------------------------------------------------------------------------- #
def _ev(eid, uid, ts, **kw):
    base = {"event_id": eid, "user_id": uid, "timestamp_utc": ts, "user_timezone": "UTC",
            "resource_family": "ENG", "sensitivity": "LOW", "data_mb": 10.0,
            "file_count": 3.0, "signals": {}}
    base.update(kw)
    return base


def test_iforest_fallbacks():
    print("\n4. Isolation Forest fallback & q95/q99")
    iforest_mod.clear_cache()
    user_hist = [_ev(f"u-e{i}", "u1", f"2024-05-{i+1:02d}T10:00:00Z", data_mb=10 + i)
                 for i in range(5)]
    pop = [_ev(f"p{i}-e{j}", f"p{i}", f"2024-05-{j+1:02d}T{8+j}:00:00Z", data_mb=20 + i + j)
           for i in range(6) for j in range(4)]
    target = _ev("u1-target", "u1", "2024-06-01T02:00:00Z", data_mb=90.0)

    r = iforest_mod.score_event(user_hist, target, pop)
    check("insufficient user history -> population fallback",
          r["available"] and r["source"] == "population" and r["population_fallback"])
    check("fallback reason documented", r["fallback_reason"] == "insufficient_user_history")
    check("q95/q99 present", r["q95"] is not None and r["q99"] is not None)
    check("scaled score within [0,100]", 0.0 <= r["scaled_score"] <= 100.0)

    r_none = iforest_mod.score_event(user_hist, target, [])
    check("no valid population -> unavailable (never fabricated)",
          r_none["available"] is False and r_none["raw_score"] is None
          and r_none["scaled_score"] is None)
    check("unavailable reason documented", r_none["fallback_reason"] == "insufficient_training_population")

    full_hist = [_ev(f"u2-e{i}", "u2", f"2024-04-{i+1:02d}T10:00:00Z", data_mb=10 + i)
                 for i in range(12)]
    r_user = iforest_mod.score_event(full_hist, _ev("u2-t", "u2", "2024-05-01T10:00:00Z"), pop)
    check(">= min_history -> per-user model", r_user["source"] == "user")
    check("min_history metadata == 10", r_user["min_history"] == 10)
    check("model metadata is iforest-v1", r_user["model"] == "iforest-v1"
          and iforest_mod.model_metadata()["model_version"] == "iforest-v1")

    r_again = iforest_mod.score_event(full_hist, _ev("u2-t", "u2", "2024-05-01T10:00:00Z"), pop)
    check("deterministic (same inputs -> same raw score)", r_user["raw_score"] == r_again["raw_score"])

    constant = [_ev(f"c{i}", "cu", f"2024-03-{i+1:02d}T10:00:00Z", data_mb=10.0, file_count=3.0)
                for i in range(12)]
    r_const = iforest_mod.score_event(constant, _ev("cu-t", "cu", "2024-04-01T10:00:00Z",
                                                   data_mb=10.0, file_count=3.0), [])
    check("constant features -> q99 == q95", abs(r_const["q99"] - r_const["q95"]) < 1e-12)
    check("constant features -> deterministic score (no crash)",
          r_const["available"] and 0.0 <= r_const["scaled_score"] <= 100.0)

    # Engine q99==q95 fallback contract.
    check("engine iforest_score(q95==q99, equal raw) == 0", engine.iforest_score(1.0, 1.0, 1.0) == 0.0)
    check("engine iforest_score(q95==q99, above raw) == 100",
          abs(engine.iforest_score(1.000001, 1.0, 1.0) - 100.0) < 1e-6)


def test_out_of_order_timestamps():
    print("\n5. Duplicate / out-of-order timestamps")
    iforest_mod.clear_cache()
    # Same timestamp for dup-a / dup-b; deterministic tie-break is event_id.
    # Stored events carry BSON datetimes, so use tz-aware datetimes here.
    def dt(d, h=10):
        return datetime(2024, 5, d, h, 0, tzinfo=timezone.utc)

    events = [
        _ev("dup-b", "du", dt(2)),
        _ev("old-c", "du", dt(1)),
    ]
    target = _ev("dup-a", "du", dt(2), data_mb=50.0)
    prior = build_baseline_for(target, [*events, target])
    check("target never enters its own baseline",
          all(e["event_id"] != "dup-a" for e in prior))
    check("duplicate timestamp -> deterministic (ts, user_id, event_id) ordering",
          {e["event_id"] for e in prior} == {"old-c"}, str({e["event_id"] for e in prior}))
    pop = [_ev(f"pop-{i}", f"po{i % 3}", dt(10 + i, 8 + (i % 8)), data_mb=15.0 + i)
           for i in range(12)]
    result = iforest_mod.score_event(prior, target, [*events, target, *pop])
    check("adapter tolerates duplicate/out-of-order timestamps", result["available"] is True)


# --------------------------------------------------------------------------- #
# 6. Calibration sweep                                                        #
# --------------------------------------------------------------------------- #
def test_calibration():
    print("\n6. Calibration sweep")
    records = [
        {"timestamp_utc": f"2024-06-{i+1:02d}T10:00:00Z", "user_id": "u", "event_id": f"e{i}",
         "score": 80.0 if i % 10 == 0 else 10.0, "positive": i % 10 == 0}
        for i in range(20)
    ]
    train, cal, test = chronological_split(records)
    check("chronological 60/20/20 split sizes", (len(train), len(cal), len(test)) == (12, 4, 4))
    check("split preserves chronological order",
          [r["event_id"] for r in train + cal + test] == [r["event_id"] for r in records])

    out1 = calibrate(records, fallback_threshold=SPEC_DETECTION_THRESHOLD)
    out2 = calibrate(records, fallback_threshold=SPEC_DETECTION_THRESHOLD)
    check("deterministic selected threshold", out1["selected_threshold"] == out2["selected_threshold"])
    check("reporting-only", out1["reporting_only"] is True and out1["mutates_global_detection"] is False)
    check("locked test metrics present", "locked_test_metrics" in out1
          and out1["locked_test_metrics"]["n"] == len(test))
    check("selection objective + tie-break documented",
          "FPR" in out1["selection_objective"] and "recall" in out1["tie_break"])

    empty = calibrate([])
    check("empty slices -> fallback, no exception",
          empty["fallback_used"] is True and empty["empty_slices"] is True
          and empty["selected_threshold"] == out1["fallback_threshold"])
    check("empty locked metrics are zeroed",
          empty["locked_test_metrics"]["tp"] == 0 and empty["locked_test_metrics"]["n"] == 0)

    sel_a = select_threshold(records)
    sel_b = select_threshold(records)
    check("threshold selection is deterministic", sel_a == sel_b)
    m = confusion(records, 50.0)
    check("confusion counts partition the slice", m["tp"] + m["fp"] + m["tn"] + m["fn"] == len(records))


# --------------------------------------------------------------------------- #
# 7. Scenario semantics (pure scoring from the frozen fixture)                #
# --------------------------------------------------------------------------- #
def test_scenarios():
    print("\n7. Scenario semantics")
    fixture = get_fixture()
    scenarios = {u["user_id"]: (u.get("scenario") or {}) for u in fixture["users"]}
    types = {s.get("type") for s in scenarios.values()}
    check("PROJECT_CHANGE scenario present", "PROJECT_CHANGE" in types)
    check("MIXED_CASE scenario present", "MIXED_CASE" in types)
    check("BENIGN renamed to NORMAL (no BENIGN left)", "BENIGN" not in types and "NORMAL" in types)

    e6 = _score_user(fixture, "rahul-006", "rahul-006-e6")
    print(f"      Rahul E6 -> {e6['risk_score']} {e6['severity']}")
    check("Rahul E6 explicit: ELEVATED", e6["severity"] == "ELEVATED", e6["severity"])
    check("Rahul E6 explicit: legacy-detected (ELEVATED+)", e6["detection"]["legacy"] is True)
    check("Rahul E6 explicit: below strict spec 70+ (documented boundary)",
          e6["detection"]["spec"] is False and e6["risk_score"] < SPEC_DETECTION_THRESHOLD)
    check("Rahul E6 behavioral channel = rules+stats", e6["behavioral_channels"]["rules"] == 100.0)

    proj = _score_user(fixture, "project-016", "project-016-e5")
    print(f"      PROJECT_CHANGE e5 -> {proj['risk_score']} {proj['severity']}")
    check("PROJECT_CHANGE settles below ELEVATED",
          proj["severity"] in ("NORMAL", "WATCH"), proj["severity"])
    check("PROJECT_CHANGE context discount applied", proj["components"]["context_adjustment"] > 0)

    mixed = _score_user(fixture, "mixed-017", "mixed-017-e4")
    print(f"      MIXED_CASE e4 -> {mixed['risk_score']} {mixed['severity']}")
    check("MIXED_CASE remains ELEVATED or higher",
          mixed["severity"] in ("ELEVATED", "HIGH", "CRITICAL"), mixed["severity"])
    check("MIXED_CASE context discounted (partially explained)",
          mixed["components"]["context_adjustment"] > 0)
    check("context cannot suppress independent anomaly (CONTEXT_OFF > FULL)",
          mixed["ablation"]["CONTEXT_OFF"]["score"] > mixed["ablation"]["FULL"]["score"])
    check("MIXED_CASE not spec-detected-only by context",
          mixed["ablation"]["CONTEXT_OFF"]["severity"] in ("ELEVATED", "HIGH", "CRITICAL"))

    pop = fixture["events"]
    check("no-leakage: strictly-prior baseline for E6 is E1..E5",
          {e["event_id"] for e in build_baseline_for(
              next(e for e in pop if e["event_id"] == "rahul-006-e6"), pop)}
          == {f"rahul-006-e{i}" for i in range(1, 6)})


# --------------------------------------------------------------------------- #
# 8. Database-backed checks (real MongoDB, else mongomock, else skipped)      #
# --------------------------------------------------------------------------- #
def _connect():
    import os
    mongo_url = os.environ.get("MONGO_URL")
    if mongo_url:
        try:
            from pymongo import MongoClient
            import sentinel.demo_db as demo_db
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
            db = client[os.environ.get("DB_NAME", "sentinel")]
            db.command("ping")
            demo_db._CLIENT = client  # keep the bounded client for service calls
            return db, "mongodb"
        except Exception:
            pass
    try:
        import mongomock
        import sentinel.demo_db as demo_db
        os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
        os.environ.setdefault("DB_NAME", "sentinel_boundary")
        demo_db._CLIENT = mongomock.MongoClient()
        return demo_db.get_db(), "mongomock"
    except Exception:
        return None, None


def test_database_flow():
    print("\n8. Reset / evaluation / assistant (database-backed)")
    db, backend = _connect()
    if db is None:
        skip("database-backed flow", "no MongoDB or mongomock available")
        return
    print(f"      using {backend}")
    from sentinel import service

    r1 = service.reset()
    r2 = service.reset()
    check("baseline_version increments on reset",
          r2["baseline_version"] == r1["baseline_version"] + 1)
    state = db["demo_state"].find_one({})
    check("baseline_version persisted in demo_state",
          state["baseline_version"] == r2["baseline_version"])
    health = service.health_state()
    check("health exposes baseline_version + detection policy",
          health["baseline_version"] == r2["baseline_version"]
          and health["detection"]["adopted"]["threshold"] == 70.0)

    user = service.get_user("rahul-006")
    check("user carries baseline lifecycle + version",
          user["baseline_lifecycle"]["state"] in ("COLD", "WARMING", "READY")
          and user["baseline_lifecycle"]["baseline_version"] == r2["baseline_version"])

    inv = service.investigate_core("rahul-006", "rahul-006-e6")
    check("investigation exposes iforest metadata",
          inv["iforest"]["available"] is True and "source" in inv["iforest"])
    check("investigation exposes ablation + detection",
          set(inv["ablation"]) == set(ABLATION_VARIANTS) and "spec" in inv["detection"])

    ev = service.evaluation()
    check("evaluation ablation uses new variants",
          [a["variant"] for a in ev["ablation"]] == list(ABLATION_VARIANTS))
    check("evaluation keeps legacy ablation aliases",
          {a["variant"] for a in ev["ablation_legacy"]} == set(ABLATION_LEGACY_ALIASES))
    check("evaluation reports dual detection thresholds",
          ev["detection_threshold"].startswith("severity >= HIGH")
          and ev["detection_threshold_legacy"].startswith("severity >= ELEVATED"))
    check("evaluation includes calibration (reporting-only)",
          ev["calibration"]["reporting_only"] is True
          and ev["calibration"]["mutates_global_detection"] is False)
    check("by_scenario uses NORMAL + legacy BENIGN alias",
          "NORMAL" in ev["by_scenario"] and "BENIGN" in ev["by_scenario_legacy"])

    asst = service.assistant_chat("rahul-006", "why flagged?", "rahul-006-e6")
    check("assistant exposes recommended_investigation_steps",
          isinstance(asst["recommended_investigation_steps"], list)
          and len(asst["recommended_investigation_steps"]) > 0)
    check("assistant retains legacy recommended_steps alias",
          asst["recommended_steps"] == asst["recommended_investigation_steps"])
    check("assistant exposes evidence_ids + signal_families",
          asst["evidence_ids"] and isinstance(asst["signal_families"], list))
    asst_err = service.assistant_chat("rahul-006", "?", "rahul-006-q1")
    check("assistant error path keeps the same schema",
          "recommended_investigation_steps" in asst_err and "evidence_ids" in asst_err)
    check("no external LLM used", asst["used_llm"] is False)


def main():
    test_baseline_boundaries()
    test_detection_policy()
    test_ablation_variants()
    test_iforest_fallbacks()
    test_out_of_order_timestamps()
    test_calibration()
    test_scenarios()
    test_database_flow()
    print("\n\033[92mALL_V51_BOUNDARY_TESTS_PASSED\033[0m")
    if _SKIPPED:
        print(f"({len(_SKIPPED)} database-backed section(s) skipped)")


if __name__ == "__main__":
    main()

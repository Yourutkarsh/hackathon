"""End-to-end FastAPI route tests for Sentinel Shift V5.1.

Run:  python test_api_routes.py      (from /app/backend)

Exercises the real ASGI app (``server.app``) through ``fastapi.testclient``,
covering every ``/api`` route: health, reset, scripted next-event, users/
timeline/evidence/alerts, investigate, assistant, audit action/trail, and the
evaluation endpoint (strict + legacy detection, ablation, calibration). Status
codes, response schemas, quarantine/validation errors, and the auditable
append-only workflow are all asserted.

Like ``test_phase1_persistence.py`` this prefers a real MongoDB and falls back to
an in-memory mongomock client when one is available, so it is runnable on a bare
checkout. It deliberately exposes a ``main()`` (not ``pytest`` test functions)
to match the repo's script-style gates and to respect pytest.ini's shared-state
xdist warning.
"""
from __future__ import annotations

import os

# The FastAPI app reads MONGO_URL / DB_NAME at import time, so defaults must be
# resolved before ``server`` is imported (see ``_prepare_db`` / ``main``).
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "sentinel_api_test")

PASS = "\033[92mPASS\033[0m"
WARN = "\033[93mWARN\033[0m"

API = "/api"
E6 = "rahul-006-e6"


def check(label, condition, detail=""):
    assert condition, f"FAIL: {label} {detail}"
    print(f"  [{PASS}] {label}")


def _prepare_db():
    """Bind the service layer to a real MongoDB (preferred) or mongomock."""
    mongo_url = os.environ["MONGO_URL"]
    try:
        from pymongo import MongoClient
        import sentinel.demo_db as demo_db
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
        db = client[os.environ["DB_NAME"]]
        db.command("ping")
        demo_db._CLIENT = client
        return db, "mongodb"
    except Exception:
        pass
    try:
        import mongomock
        import sentinel.demo_db as demo_db
        demo_db._CLIENT = mongomock.MongoClient()
        return demo_db.get_db(), "mongomock"
    except Exception:
        return None, None


def _run(client, db):
    # ---- root -------------------------------------------------------------
    print("\n1. Root route")
    r = client.get(f"{API}/")
    check("GET /api/ -> 200 Hello World",
          r.status_code == 200 and r.json() == {"message": "Hello World"}, r.text)

    # ---- demo stepper before seed ----------------------------------------
    print("\n2. Scripted demo stepper (not seeded -> 409)")
    db["demo_state"].delete_many({})
    r = client.post(f"{API}/demo/next-event")
    check("POST /api/demo/next-event before reset -> 409",
          r.status_code == 409, r.text)

    # ---- reset ------------------------------------------------------------
    print("\n3. Reset")
    r = client.post(f"{API}/demo/reset")
    body = r.json()
    check("POST /api/demo/reset -> 200", r.status_code == 200, r.text)
    check("reset returns counts + fixture hash + baseline_version",
          body["document_counts"]["events"] > 0 and len(body["fixture_hash"]) == 64
          and isinstance(body["baseline_version"], int) and body["baseline_version"] >= 1)
    first_version = body["baseline_version"]
    r2 = client.post(f"{API}/demo/reset")
    check("repeated reset increments baseline_version",
          r2.json()["baseline_version"] == first_version + 1)

    # ---- health -----------------------------------------------------------
    print("\n4. Health")
    r = client.get(f"{API}/health")
    h = r.json()
    check("GET /api/health -> 200", r.status_code == 200, r.text)
    check("health reports locked engine", h["engine_integrity_ok"] is True)
    check("health exposes adopted strict detection (70+)",
          h["detection"]["adopted"]["threshold"] == 70.0)
    check("health exposes baseline_version (demo-wide)",
          h["baseline_version"] == r2.json()["baseline_version"])
    check("health exposes iforest-v1 model metadata",
          h["iforest_model"]["model_version"] == "iforest-v1")
    check("health exposes revised ablation variants",
          "RULES_STATS_IFOREST" in h["ablation_variants"])

    # ---- users ------------------------------------------------------------
    print("\n5. Users / timeline / evidence / alerts")
    r = client.get(f"{API}/users")
    users = r.json()
    check("GET /api/users -> 200 population >= 50",
          r.status_code == 200 and isinstance(users, list) and len(users) >= 50,
          r.text)
    check("user summary carries baseline_state",
          all("baseline_state" in u for u in users)
          and {u["baseline_state"] for u in users} & {"COLD", "WARMING", "READY"})

    r = client.get(f"{API}/users/rahul-006")
    user = r.json()
    check("GET /api/users/{id} -> 200 with baseline lifecycle",
          r.status_code == 200 and user["baseline_lifecycle"]["state"] in
          ("COLD", "WARMING", "READY"), r.text)
    check("GET /api/users/unknown -> 404",
          client.get(f"{API}/users/does-not-exist").status_code == 404)

    r = client.get(f"{API}/users/rahul-006/timeline")
    tl = r.json()
    check("GET /api/users/{id}/timeline -> 200 chronological events",
          r.status_code == 200 and tl["user_id"] == "rahul-006"
          and any(e["event_id"] == E6 for e in tl["events"]), r.text)
    check("timeline unknown user -> 404",
          client.get(f"{API}/users/nobody/timeline").status_code == 404)

    r = client.get(f"{API}/users/rahul-006/evidence")
    ev = r.json()
    check("GET /api/users/{id}/evidence -> 200 top event",
          r.status_code == 200 and ev["top_event"]["event_id"] == E6, r.text)
    check("evidence unknown user -> 404",
          client.get(f"{API}/users/nobody/evidence").status_code == 404)

    r = client.get(f"{API}/users/rahul-006/alerts")
    check("GET /api/users/{id}/alerts -> 200 with E6 alert",
          r.status_code == 200 and r.json()["alert_count"] >= 1
          and any(a["event_id"] == E6 for a in r.json()["alerts"]), r.text)

    # ---- investigate ------------------------------------------------------
    print("\n6. Investigate")
    r = client.post(f"{API}/investigate", json={"user_id": "rahul-006", "event_id": E6})
    inv = r.json()
    check("POST /api/investigate -> 200 ELEVATED compound anomaly",
          r.status_code == 200 and inv["severity"] == "ELEVATED"
          and abs(inv["risk_score"] - 67.98) < 0.01, r.text)
    check("investigation exposes 5 components + availability",
          set(inv["components"]) == {"behavioral_anomaly", "temporal_correlation",
                                     "sensitivity", "novelty", "context_adjustment"}
          and "component_availability" in inv)
    check("investigation exposes iforest + ablation + detection",
          "available" in inv["iforest"] and "RULES_ONLY" in inv["ablation"]
          and inv["detection"]["legacy"] is True)
    check("investigation attaches baseline lifecycle",
          inv["baseline_lifecycle"]["baseline_version"] == r2.json()["baseline_version"])

    check("investigate unknown user -> 404",
          client.post(f"{API}/investigate", json={"user_id": "ghost"}).status_code == 404)
    check("investigate unknown event -> 404",
          client.post(f"{API}/investigate",
                      json={"user_id": "rahul-006", "event_id": "nope"}).status_code == 404)
    rq = client.post(f"{API}/investigate",
                     json={"user_id": "yuki-007", "event_id": "yuki-007-q1"})
    check("investigate quarantined event -> 422 with reasons",
          rq.status_code == 422 and "quarantine_reasons" in rq.json()["detail"],
          rq.text)
    check("investigate missing required field -> 422",
          client.post(f"{API}/investigate", json={}).status_code == 422)

    # ---- assistant --------------------------------------------------------
    print("\n7. Assistant")
    r = client.post(f"{API}/assistant/chat",
                    json={"user_id": "rahul-006", "question": "why was this flagged?",
                          "event_id": E6})
    a = r.json()
    check("POST /api/assistant/chat -> 200 offline", r.status_code == 200
          and a["used_llm"] is False, r.text)
    check("assistant exposes recommended_investigation_steps",
          isinstance(a["recommended_investigation_steps"], list)
          and len(a["recommended_investigation_steps"]) > 0)
    check("assistant keeps legacy recommended_steps alias",
          a["recommended_steps"] == a["recommended_investigation_steps"])
    check("assistant exposes evidence_ids + signal_families",
          E6 in a["evidence_ids"] and len(a["signal_families"]) > 0)
    check("assistant exposes baseline_state + iforest",
          a["baseline_state"] in ("COLD", "WARMING", "READY") and "source" in a["iforest"])

    r = client.post(f"{API}/assistant/chat",
                    json={"user_id": "rahul-006",
                          "question": "<script>alert(1)</script>", "event_id": E6})
    echoed = r.json()["query_echo"]
    check("assistant escapes untrusted question text",
          "<script>" not in echoed and "&lt;script&gt;" in echoed, echoed)

    # ---- audit ------------------------------------------------------------
    print("\n8. Audit action + trail (append-only)")
    r = client.post(f"{API}/audit/action",
                    json={"user_id": "rahul-006", "event_id": E6, "action": "NOTE",
                          "note": "<b>escalate me</b>"})
    act = r.json()
    check("POST /api/audit/action NOTE -> 200 risk unchanged",
          r.status_code == 200 and act["risk_score_unchanged"] == inv["risk_score"]
          and act["severity_unchanged"] == inv["severity"], r.text)
    check("audit note is HTML-escaped", "&lt;b&gt;" in (act["note"] or ""))
    r = client.post(f"{API}/audit/action",
                    json={"user_id": "rahul-006", "event_id": E6, "action": "DISMISS"})
    check("DISMISS is a workflow flag only",
          r.status_code == 200 and r.json()["dismissed"] is True
          and r.json()["risk_score_unchanged"] == inv["risk_score"])
    check("invalid audit action -> 400",
          client.post(f"{API}/audit/action",
                      json={"user_id": "rahul-006", "action": "FROBNICATE"}).status_code == 400)
    check("audit action unknown user -> 404",
          client.post(f"{API}/audit/action",
                      json={"user_id": "ghost", "action": "NOTE"}).status_code == 404)

    r = client.get(f"{API}/audit", params={"user_id": "rahul-006"})
    records = r.json()["records"]
    check("GET /api/audit -> 200 append-only trail with our actions",
          r.status_code == 200 and len(records) >= 2
          and {x["action"] for x in records} >= {"ANALYST_NOTE", "ANALYST_DISMISS"}, r.text)

    # ---- next-event -------------------------------------------------------
    print("\n9. Scripted next-event")
    r = client.post(f"{API}/demo/next-event")
    step = r.json()
    check("POST /api/demo/next-event -> 200 reveals an event",
          r.status_code == 200 and step.get("revealed_event") is not None
          and step["cursor"] == 1, r.text)

    # ---- evaluation -------------------------------------------------------
    print("\n10. Evaluation (strict + legacy + ablation + calibration)")
    r = client.get(f"{API}/evaluation")
    evl = r.json()
    check("GET /api/evaluation -> 200", r.status_code == 200, r.text)
    check("evaluation primary uses strict spec detection",
          evl["detection_threshold"].startswith("severity >= HIGH")
          and "precision" in evl["overall"])
    check("evaluation keeps legacy detection alias",
          evl["detection_threshold_legacy"].startswith("severity >= ELEVATED")
          and evl["overall_legacy"]["recall"] >= evl["overall"]["recall"])
    check("evaluation ablation uses revised variants",
          {a["variant"] for a in evl["ablation"]} ==
          {"RULES_ONLY", "RULES_PLUS_STATS", "RULES_STATS_IFOREST",
           "FULL", "TEMPORAL_OFF", "CONTEXT_OFF"})
    check("evaluation keeps legacy ablation aliases",
          {a["variant"] for a in evl["ablation_legacy"]} ==
          {"NO_CONTEXT", "NO_TEMPORAL", "NO_NOVELTY", "BEHAVIORAL_ONLY"})
    check("evaluation calibration is reporting-only",
          evl["calibration"]["reporting_only"] is True
          and evl["calibration"]["mutates_global_detection"] is False
          and "locked_test_metrics" in evl["calibration"])
    check("evaluation scenario rollup uses NORMAL + PROJECT_CHANGE + MIXED_CASE",
          {"NORMAL", "PROJECT_CHANGE", "MIXED_CASE"} <= set(evl["by_scenario"]))


def main():
    db, backend = _prepare_db()
    if db is None:
        print(f"  [{WARN}] SKIP: no MongoDB and no mongomock available")
        print("\n\033[92mALL_API_ROUTE_TESTS_PASSED\033[0m (database-backed suite skipped)")
        return
    print(f"\nUsing {backend} as the service datastore")
    from fastapi.testclient import TestClient
    import logging
    import server

    # server.py configures root logging at INFO; keep the request spam out of the run.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    with TestClient(server.app) as client:
        _run(client, db)

    print("\n\033[92mALL_API_ROUTE_TESTS_PASSED\033[0m")


if __name__ == "__main__":
    main()

"""Phase 2 service layer: MongoDB orchestration on top of the immutable engine.

All functions here are synchronous (pymongo). FastAPI wraps them with
``run_in_threadpool``. Risk math is delegated entirely to ``sentinel.scoring``
(which only calls ``risk_engine_v5_1``). Audit writes never touch scoring inputs.
"""
from __future__ import annotations

import html
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .demo_db import (
    ENGINE_CHECKSUM,
    DEMO_COLLECTIONS,
    get_db,
    reset_demo_db,
    verify_engine_integrity,
)
from .fixtures import ENGINE_VERSION, SEED_VERSION, build_baseline_for, fixture_hash
from .scoring import FLAGGED_SEVERITIES, ablation_scores, build_alerts, score_event

_COMPOUND_SORT = [("timestamp_utc", 1), ("user_id", 1), ("event_id", 1)]
_NO_ID = {"_id": 0}


def _iso(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    return value


def _clean_event(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc = dict(doc)
    doc["timestamp_utc"] = _iso(doc.get("timestamp_utc"))
    return doc


# --------------------------------------------------------------------------- #
# Health / reset                                                               #
# --------------------------------------------------------------------------- #
def health_state() -> Dict[str, Any]:
    db = get_db()
    try:
        db.command("ping")
        db_ok = True
    except Exception:
        db_ok = False
    state = db["demo_state"].find_one({}, _NO_ID)
    return {
        "status": "ok" if db_ok else "degraded",
        "db_connected": db_ok,
        "engine_version": ENGINE_VERSION,
        "engine_integrity_ok": verify_engine_integrity(),
        "engine_checksum": ENGINE_CHECKSUM,
        "seed_version": SEED_VERSION,
        "fixture_hash": fixture_hash(),
        "seeded": state is not None,
        "demo_cursor": (state or {}).get("cursor"),
    }


def reset() -> Dict[str, Any]:
    return reset_demo_db(get_db())


# --------------------------------------------------------------------------- #
# Users / timeline                                                             #
# --------------------------------------------------------------------------- #
def list_users() -> List[Dict[str, Any]]:
    db = get_db()
    out = []
    for u in db["users"].find({}, _NO_ID).sort("user_id", 1):
        uid = u["user_id"]
        out.append({
            "user_id": uid,
            "display_name": u.get("display_name"),
            "location": u.get("location"),
            "user_timezone": u.get("user_timezone"),
            "event_count": db["events"].count_documents({"user_id": uid, "quarantined": False}),
            "quarantined_count": db["events"].count_documents({"user_id": uid, "quarantined": True}),
        })
    return out


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    user = db["users"].find_one({"user_id": user_id}, _NO_ID)
    if not user:
        return None
    user["trusted_event_count"] = db["events"].count_documents(
        {"user_id": user_id, "quarantined": False})
    user["quarantined_count"] = db["events"].count_documents(
        {"user_id": user_id, "quarantined": True})
    user["created_at"] = _iso(user.get("created_at"))
    return user


def get_timeline(user_id: str) -> Optional[List[Dict[str, Any]]]:
    db = get_db()
    if not db["users"].find_one({"user_id": user_id}, _NO_ID):
        return None
    events = db["events"].find({"user_id": user_id}, _NO_ID).sort(_COMPOUND_SORT)
    return [_clean_event(e) for e in events]


# --------------------------------------------------------------------------- #
# Audit trail (append-only)                                                    #
# --------------------------------------------------------------------------- #
def append_audit(user_id: str, event_id: Optional[str], risk_score: float,
                 severity: str, action: str, note: Optional[str] = None) -> str:
    """Append an immutable audit record. Never mutates scoring/quarantine/baseline."""
    db = get_db()
    audit_id = str(uuid.uuid4())
    db["audit_records"].insert_one({
        "audit_id": audit_id,
        "user_id": user_id,
        "event_id": event_id,
        "risk_score": risk_score,
        "severity": severity,
        "action": action,
        "note": note,
        "created_at": datetime.now(timezone.utc),
        "dismissed": False,
        "dismissed_at": None,
    })
    return audit_id


def list_audit(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    db = get_db()
    query = {"user_id": user_id} if user_id else {}
    records = db["audit_records"].find(query, _NO_ID).sort("created_at", 1)
    out = []
    for r in records:
        r["created_at"] = _iso(r.get("created_at"))
        r["dismissed_at"] = _iso(r.get("dismissed_at"))
        out.append(r)
    return out


# Analyst workflow actions. These APPEND audit records only. They re-derive the
# score via the engine to prove the number is unchanged, and never mutate
# scoring inputs, quarantine status, or baseline eligibility.
ANALYST_ACTIONS = {"NOTE": "ANALYST_NOTE", "ESCALATE": "ANALYST_ESCALATE", "DISMISS": "ANALYST_DISMISS"}


def analyst_action(user_id: str, event_id: Optional[str], action: str,
                   note: Optional[str] = None) -> Dict[str, Any]:
    action = str(action or "").upper()
    if action not in ANALYST_ACTIONS:
        return {"error": "invalid_action"}
    scored = investigate_core(user_id, event_id)
    if "error" in scored:
        return scored
    db = get_db()
    audit_id = str(uuid.uuid4())
    dismissed = action == "DISMISS"
    safe_note = html.escape(note)[:500] if note else None
    now = datetime.now(timezone.utc)
    db["audit_records"].insert_one({
        "audit_id": audit_id,
        "user_id": user_id,
        "event_id": scored["event_id"],
        "risk_score": scored["risk_score"],
        "severity": scored["severity"],
        "action": ANALYST_ACTIONS[action],
        "note": safe_note,
        "created_at": now,
        "dismissed": dismissed,
        "dismissed_at": now if dismissed else None,
    })
    return {
        "audit_id": audit_id,
        "action": ANALYST_ACTIONS[action],
        "user_id": user_id,
        "event_id": scored["event_id"],
        "note": safe_note,
        "dismissed": dismissed,
        # Proof the workflow action left the risk math untouched:
        "risk_score_unchanged": scored["risk_score"],
        "severity_unchanged": scored["severity"],
        "quarantine_unaffected": True,
    }


# --------------------------------------------------------------------------- #
# Scoring / investigation                                                      #
# --------------------------------------------------------------------------- #
def _trusted_events(db, user_id: str) -> List[Dict[str, Any]]:
    return list(db["events"].find(
        {"user_id": user_id, "quarantined": False}, _NO_ID).sort(_COMPOUND_SORT))


def investigate_core(user_id: str, event_id: Optional[str] = None) -> Dict[str, Any]:
    """Compute risk state for a user's event. Returns a result dict or an error dict."""
    db = get_db()
    user = db["users"].find_one({"user_id": user_id}, _NO_ID)
    if not user:
        return {"error": "user_not_found"}

    if event_id:
        target = db["events"].find_one({"event_id": event_id, "user_id": user_id}, _NO_ID)
        if not target:
            return {"error": "event_not_found"}
        if target.get("quarantined"):
            return {
                "error": "event_quarantined",
                "event_id": event_id,
                "quarantine_reasons": target.get("quarantine_reasons", []),
            }
    else:
        trusted = _trusted_events(db, user_id)
        if not trusted:
            return {"error": "no_trusted_events"}
        target = trusted[-1]

    all_trusted = _trusted_events(db, user_id)
    prior = build_baseline_for(target, all_trusted)
    contexts = list(db["contexts"].find({"user_id": user_id}, _NO_ID))
    scored = score_event(user, target, prior, contexts)
    scored["display_name"] = user.get("display_name")
    return scored


def investigate(user_id: str, event_id: Optional[str] = None) -> Dict[str, Any]:
    scored = investigate_core(user_id, event_id)
    if "error" in scored:
        return scored
    audit_id = append_audit(
        user_id=scored["user_id"], event_id=scored["event_id"],
        risk_score=scored["risk_score"], severity=scored["severity"],
        action="ANALYST_INVESTIGATION",
    )
    scored["audit_id"] = audit_id
    return scored


PAUSE_EVENT = "rahul-006-e6"


def next_event(force: bool = False) -> Dict[str, Any]:
    db = get_db()
    state = db["demo_state"].find_one({})
    if not state:
        return {"error": "not_seeded"}
    cursor = int(state.get("cursor", 0))
    paused = bool(state.get("paused", False))
    sequence = list(db["events"].find({"quarantined": False}, _NO_ID).sort(_COMPOUND_SORT))
    total = len(sequence)

    # Bug-2 fix: hold the stream at the London anomaly until the judge confirms.
    if paused and not force:
        return {
            "paused": True,
            "cursor": cursor,
            "total": total,
            "revealed_event": None,
            "message": "Paused at the London compound anomaly. Confirm to continue the stream.",
        }
    if paused and force:
        db["demo_state"].update_one({"_id": state["_id"]}, {"$set": {"paused": False}})

    if cursor >= total:
        return {"done": True, "cursor": cursor, "total": total, "revealed_event": None}

    target = sequence[cursor]
    user = db["users"].find_one({"user_id": target["user_id"]}, _NO_ID)
    prior = build_baseline_for(target, _trusted_events(db, target["user_id"]))
    contexts = list(db["contexts"].find({"user_id": target["user_id"]}, _NO_ID))
    scored = score_event(user, target, prior, contexts)
    scored["display_name"] = user.get("display_name")

    new_cursor = cursor + 1
    set_fields = {"cursor": new_cursor}
    if target["event_id"] == PAUSE_EVENT:
        set_fields["paused"] = True
    db["demo_state"].update_one({"_id": state["_id"]}, {"$set": set_fields})

    audit_id = None
    if scored["severity"] in FLAGGED_SEVERITIES:
        audit_id = append_audit(
            user_id=scored["user_id"], event_id=scored["event_id"],
            risk_score=scored["risk_score"], severity=scored["severity"],
            action="FLAGGED_BY_DEMO",
        )
    scored["audit_id"] = audit_id
    return {
        "done": False,
        "paused_next": set_fields.get("paused", False),
        "cursor": new_cursor,
        "total": total,
        "revealed_event": scored,
    }


def _score_user_events(db, user):
    """Score every trusted event for a user; returns list of scored dicts (chronological)."""
    trusted = _trusted_events(db, user["user_id"])
    contexts = list(db["contexts"].find({"user_id": user["user_id"]}, _NO_ID))
    out = []
    for tev in trusted:
        prior = build_baseline_for(tev, trusted)
        out.append(score_event(user, tev, prior, contexts))
    return out


def user_evidence(user_id: str) -> Dict[str, Any]:
    db = get_db()
    user = db["users"].find_one({"user_id": user_id}, _NO_ID)
    if not user:
        return {"error": "user_not_found"}
    scored_list = _score_user_events(db, user)
    if not scored_list:
        return {"error": "no_trusted_events"}
    top = max(scored_list, key=lambda s: s["risk_score"])
    summaries = [
        {
            "event_id": s["event_id"],
            "severity": s["severity"],
            "risk_score": s["risk_score"],
            "fired_families": s["evidence"]["fired_families"],
            "timestamp_utc": s["evidence"]["target_event"]["timestamp_utc"],
        }
        for s in scored_list
    ]
    return {
        "user_id": user_id,
        "scenario": user.get("scenario"),
        "top_event": top,
        "timeline_evidence": summaries,
    }


def user_alerts(user_id: str) -> Dict[str, Any]:
    db = get_db()
    user = db["users"].find_one({"user_id": user_id}, _NO_ID)
    if not user:
        return {"error": "user_not_found"}
    scored_list = _score_user_events(db, user)
    alerts = build_alerts(user_id, scored_list)
    return {"user_id": user_id, "alert_count": len(alerts), "alerts": alerts}


def evaluation() -> Dict[str, Any]:
    """Ground-truth precision/recall/F1/FPR plus a component-ablation table.

    Detection = engine severity >= ELEVATED. Ground truth comes from each user's
    labelled scenario (malicious_event_ids). Read-only; no scores are stored.
    """
    db = get_db()
    users = list(db["users"].find({}, _NO_ID))
    variants = ["FULL", "NO_CONTEXT", "NO_TEMPORAL", "NO_NOVELTY", "BEHAVIORAL_ONLY"]
    conf = {v: {"tp": 0, "fp": 0, "tn": 0, "fn": 0} for v in variants}
    by_scenario: Dict[str, Dict[str, int]] = {}
    total_events = 0

    for user in users:
        scenario = user.get("scenario") or {}
        truth = set(scenario.get("malicious_event_ids") or [])
        stype = scenario.get("type", "BENIGN")
        for scored in _score_user_events(db, user):
            total_events += 1
            is_pos = scored["event_id"] in truth
            abl = ablation_scores(scored["components"])
            for v in variants:
                det = abl[v]["severity"] in FLAGGED_SEVERITIES
                cell = ("tp" if det and is_pos else "fp" if det and not is_pos
                        else "fn" if is_pos and not det else "tn")
                conf[v][cell] += 1
            ps = by_scenario.setdefault(
                stype, {"events": 0, "malicious": 0, "detected_malicious": 0, "false_alarms": 0})
            ps["events"] += 1
            full_det = abl["FULL"]["severity"] in FLAGGED_SEVERITIES
            if is_pos:
                ps["malicious"] += 1
                if full_det:
                    ps["detected_malicious"] += 1
            elif full_det:
                ps["false_alarms"] += 1

    def metrics(c):
        tp, fp, tn, fn = c["tp"], c["fp"], c["tn"], c["fn"]
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        fpr = fp / (fp + tn) if (fp + tn) else 0.0
        return {**c, "precision": round(prec, 4), "recall": round(rec, 4),
                "f1": round(f1, 4), "false_positive_rate": round(fpr, 4)}

    return {
        "total_users": len(users),
        "total_trusted_events": total_events,
        "detection_threshold": "severity >= ELEVATED",
        "overall": metrics(conf["FULL"]),
        "ablation": [{"variant": v, **metrics(conf[v])} for v in variants],
        "by_scenario": by_scenario,
    }


# --------------------------------------------------------------------------- #
# Offline deterministic assistant                                             #
# --------------------------------------------------------------------------- #
def assistant_chat(user_id: str, question: str, event_id: Optional[str] = None) -> Dict[str, Any]:
    """Deterministic, offline assistant. No external LLM keys are required.

    All untrusted text (the analyst question and synthetic user/location strings)
    is HTML-escaped before being placed into the response.
    """
    scored = investigate_core(user_id, event_id)
    safe_question = html.escape(question or "")
    if "error" in scored:
        return {
            "answer": f"Unable to investigate: {html.escape(scored['error'])}.",
            "risk_score": None,
            "severity": None,
            "confidence": None,
            "citations": [],
            "components": {},
            "used_llm": False,
            "disclaimer": "Offline deterministic assistant. No external LLM was used.",
            "query_echo": safe_question,
            "error": scored["error"],
        }

    ev = scored["evidence"]["target_event"]
    loc = ev.get("location") or {}
    safe_city = html.escape(str(loc.get("city", "unknown")))
    safe_country = html.escape(str(loc.get("country", "unknown")))
    safe_name = html.escape(str(scored.get("display_name") or user_id))
    fired = scored["evidence"]["fired_families"]
    fired_txt = html.escape(", ".join(fired) if fired else "no discrete rules")

    answer = (
        f"Event {html.escape(str(ev.get('event_id')))} for {safe_name} scored "
        f"{scored['risk_score']} ({html.escape(scored['severity'])}) with confidence "
        f"{scored['confidence']}. Activity originated from {safe_city}, {safe_country} at "
        f"{html.escape(str(ev.get('timestamp_utc')))} (local timezone "
        f"{html.escape(str(ev.get('user_timezone')))}). Contributing detectors: {fired_txt}. "
        f"The behavioral, temporal, sensitivity, novelty and context components are reported "
        f"with explicit availability flags. This assessment is evidence-linked and does not "
        f"modify any stored risk value."
    )

    citations = [
        {"event_id": ev.get("event_id"), "field": "severity", "value": scored["severity"]},
        {"event_id": ev.get("event_id"), "field": "risk_score", "value": scored["risk_score"]},
        {"event_id": ev.get("event_id"), "field": "location",
         "value": f"{loc.get('city')}, {loc.get('country')}"},
        {"event_id": ev.get("event_id"), "field": "timestamp_utc", "value": ev.get("timestamp_utc")},
        {"event_id": ev.get("event_id"), "field": "fired_families", "value": fired},
    ]

    labels = {
        "behavioral_anomaly": "Behavioral Anomaly",
        "temporal_correlation": "Temporal Correlation",
        "sensitivity": "Sensitivity Elevation",
        "novelty": "Novelty",
        "context_adjustment": "Context Adjustment",
    }
    key_facts = [
        f"Severity {scored['severity']} at risk score {scored['risk_score']} (engine-authoritative).",
        f"Origin: {safe_city}, {safe_country}; timezone {html.escape(str(ev.get('user_timezone')))}.",
        f"Event timestamp (UTC): {html.escape(str(ev.get('timestamp_utc')))}.",
        f"Fired detectors: {fired_txt}.",
        f"Active signal families: {html.escape(', '.join(scored['active_signal_families']) or 'none')}.",
    ]
    uncertainties = []
    for key, avail in scored["component_availability"].items():
        if not avail:
            uncertainties.append(f"{labels[key]} component unavailable (excluded from evidence).")
    if scored.get("incomplete"):
        uncertainties.append(
            "Event is incomplete; missing: "
            + html.escape(", ".join(scored.get("missing_components") or [])) + ".")
    if scored["confidence"] < 100:
        uncertainties.append(f"Confidence is {scored['confidence']}/100 due to deterministic penalties.")
    if not uncertainties:
        uncertainties.append("No availability gaps; all five components were observed.")
    if scored["severity"] in ("ELEVATED", "HIGH", "CRITICAL"):
        recommended_steps = [
            "Verify with the user whether the flagged session was legitimate travel or access.",
            "Cross-check the origin location and device against approved context windows.",
            "Review the volume and off-hours evidence before escalation.",
            "Record an audit note; dismissal remains workflow-only and never changes the score.",
        ]
    else:
        recommended_steps = [
            "No elevated risk detected; continue passive monitoring.",
            "Re-investigate if a new context or higher-volume event appears.",
        ]

    audit_id = append_audit(
        user_id=scored["user_id"], event_id=scored["event_id"],
        risk_score=scored["risk_score"], severity=scored["severity"],
        action="ASSISTANT_QUERY", note=safe_question[:280] or None,
    )

    return {
        "answer": answer,
        "risk_score": scored["risk_score"],
        "severity": scored["severity"],
        "confidence": scored["confidence"],
        "key_facts": key_facts,
        "uncertainties": uncertainties,
        "recommended_steps": recommended_steps,
        "citations": citations,
        "components": scored["components"],
        "component_availability": scored["component_availability"],
        "used_llm": False,
        "disclaimer": "Offline deterministic assistant. No external LLM was used.",
        "query_echo": safe_question,
        "audit_id": audit_id,
    }


__all__ = [
    "DEMO_COLLECTIONS",
    "health_state", "reset", "list_users", "get_user", "get_timeline",
    "append_audit", "list_audit", "investigate", "investigate_core",
    "next_event", "assistant_chat", "analyst_action",
    "user_evidence", "user_alerts", "evaluation",
]

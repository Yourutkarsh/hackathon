"""Scoring pipeline for Sentinel Shift Phase 2.

This module ONLY orchestrates calls into the immutable reference engine
(``risk_engine_v5_1``). It never re-implements any formula, threshold, ordering,
or detector. Every risk number returned here comes directly from the engine.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import risk_engine_v5_1 as engine

# Severities that constitute a "flagged" investigation for the audit trail.
FLAGGED_SEVERITIES = {"ELEVATED", "HIGH", "CRITICAL"}


def _ts_iso(value: Any) -> str:
    """Return an ISO-8601 UTC string for a BSON datetime / string / None."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, str):
        return value
    return ""


def to_engine_event(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Project a stored event document into the engine's event input shape."""
    return {
        "event_id": doc.get("event_id"),
        "user_id": doc.get("user_id"),
        "timestamp_utc": _ts_iso(doc.get("timestamp_utc")),
        "user_timezone": doc.get("user_timezone"),
        "resource_family": doc.get("resource_family"),
        "sensitivity": doc.get("sensitivity"),
        "data_mb": doc.get("data_mb"),
        "file_count": doc.get("file_count"),
        "signals": dict(doc.get("signals") or {}),
    }


def _numeric_list(values: List[Any]) -> List[float]:
    return [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]


def make_baseline(user_doc: Dict[str, Any], prior_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build the engine baseline mapping from the user profile + strictly-prior events."""
    b = dict(user_doc.get("baseline") or {})
    seen = {f for f in (b.get("resource_families") or []) if isinstance(f, str)}
    for e in prior_events:
        rf = e.get("resource_family")
        if isinstance(rf, str):
            seen.add(rf)
    prior_data = _numeric_list([e.get("data_mb") for e in prior_events])
    prior_files = _numeric_list([e.get("file_count") for e in prior_events])
    return {
        "active_start_minute": b.get("active_start_minute"),
        "active_end_minute": b.get("active_end_minute"),
        "resource_families": sorted(seen),
        "data_mb_baseline": prior_data or _numeric_list(b.get("data_mb_baseline") or []),
        "file_count_baseline": prior_files or _numeric_list(b.get("file_count_baseline") or []),
        "rolling_30m_count_baseline": _numeric_list(b.get("rolling_30m_count_baseline") or []),
    }


def _engine_contexts(contexts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for c in contexts:
        out.append({
            "affected_signal_families": list(c.get("affected_signal_families") or []),
            "raw_reduction_points": c.get("raw_reduction_points", 0.0),
            "confidence": c.get("confidence", "LOW"),
            "start_utc": _ts_iso(c.get("start_utc")) or None,
            "end_utc": _ts_iso(c.get("end_utc")) or None,
        })
    return out


def score_event(
    user_doc: Dict[str, Any],
    target: Dict[str, Any],
    prior_events: List[Dict[str, Any]],
    contexts: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Compute the full risk state for ``target`` using engine functions only.

    ``prior_events`` MUST be the strictly-prior trusted events (baseline). The
    caller guarantees no current/future event is included.
    """
    contexts = contexts or []
    baseline = make_baseline(user_doc, prior_events)
    engine_event = to_engine_event(target)
    engine_prior = [to_engine_event(e) for e in prior_events]

    # Rule detector (Rules A-E) -> behavioral rule channel.
    rule_result = engine.rule_detector(engine_event, baseline)

    # Robust statistical channel from volume vs. strictly-prior baseline.
    statistical = None
    if engine_event.get("data_mb") is not None and baseline["data_mb_baseline"]:
        statistical = engine.robust_statistical_score(
            float(engine_event["data_mb"]), baseline["data_mb_baseline"]
        )

    engine_event["rule_score"] = rule_result["rule_score"]
    engine_event["rule_available"] = rule_result["rule_available"]
    if statistical is not None:
        engine_event["statistical_score"] = statistical

    # Temporal clustering over the trusted window (prior + target).
    window = engine_prior + [engine_event]
    clusters = engine.cluster_events(window)
    summaries = engine.cluster_summaries(clusters)

    # Sensitivity uses strictly-prior comparable history.
    components = engine.normalized_components(
        events=[engine_event],
        clusters=clusters,
        contexts=_engine_contexts(contexts),
        resource_history=engine_prior,
        now_utc=engine_event["timestamp_utc"] or None,
    )

    score = engine.compute_final_risk_score(components)
    severity = engine.severity_for_score(score)

    missing = list(target.get("missing_components") or [])
    confidence = engine.confidence_score(
        baseline_ready=len(prior_events) >= 3,
        timezone_available=bool(engine_event.get("user_timezone")),
        iforest_available=False,
        sensitivity_history_available=components.availability["sensitivity"],
        required_missing_fraction=len(missing) / 4.0,
    )

    # Context provenance: which contexts were time-valid at the event instant.
    now_dt = engine._parse_ts(engine_event["timestamp_utc"])
    contexts_considered = []
    for c in contexts:
        start = engine._parse_ts(_ts_iso(c.get("start_utc"))) if c.get("start_utc") else None
        end = engine._parse_ts(_ts_iso(c.get("end_utc"))) if c.get("end_utc") else None
        applicable = True
        if now_dt is not None:
            if start is not None and now_dt < start:
                applicable = False
            if end is not None and now_dt > end:
                applicable = False
        contexts_considered.append({
            "context_id": c.get("context_id"),
            "affected_signal_families": list(c.get("affected_signal_families") or []),
            "reason": c.get("reason"),
            "time_valid_at_event": applicable,
        })

    return {
        "user_id": target.get("user_id"),
        "event_id": target.get("event_id"),
        "risk_score": score,
        "severity": severity,
        "confidence": confidence,
        "components": components.values,
        "component_availability": components.availability,
        "active_signal_families": components.active_signal_families,
        "signals": dict(target.get("signals") or {}),
        "clusters": summaries,
        "incomplete": bool(target.get("incomplete")),
        "missing_components": missing,
        "evidence": {
            "target_event": {
                "event_id": target.get("event_id"),
                "timestamp_original": target.get("timestamp_original"),
                "timestamp_utc": _ts_iso(target.get("timestamp_utc")),
                "user_timezone": target.get("user_timezone"),
                "location": target.get("location"),
                "resource_family": target.get("resource_family"),
                "sensitivity": target.get("sensitivity"),
                "data_mb": target.get("data_mb"),
                "file_count": target.get("file_count"),
            },
            "baseline_event_ids": [e.get("event_id") for e in prior_events],
            "baseline_window": {
                "from": _ts_iso(prior_events[0].get("timestamp_utc")) if prior_events else None,
                "to": _ts_iso(prior_events[-1].get("timestamp_utc")) if prior_events else None,
            },
            "rule_scores": rule_result["rule_scores"],
            "fired_families": rule_result["fired_families"],
            "statistical_score": statistical,
            "contexts_considered": contexts_considered,
        },
    }


def ablation_scores(values: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    """Recompute the final score under component-ablation variants (engine-only)."""
    variants = {
        "FULL": dict(values),
        "NO_CONTEXT": {**values, "context_adjustment": 0.0},
        "NO_TEMPORAL": {**values, "temporal_correlation": 0.0},
        "NO_NOVELTY": {**values, "novelty": 0.0},
        "BEHAVIORAL_ONLY": {"behavioral_anomaly": values.get("behavioral_anomaly", 0.0)},
    }
    out = {}
    for name, v in variants.items():
        score = engine.compute_final_risk_score(v)
        out[name] = {"score": score, "severity": engine.severity_for_score(score)}
    return out


def build_alerts(user_id: str, scored_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate flagged events into alerts using the engine's Section-21 contract."""
    alerts: List[Dict[str, Any]] = []
    existing: Dict[str, str] = {}
    for scored in scored_events:
        if scored["severity"] not in FLAGGED_SEVERITIES:
            continue
        top = scored["active_signal_families"]
        ts = scored["evidence"]["target_event"]["timestamp_utc"]
        key = engine.dedup_key(user_id, top, ts)
        action = engine.resolve_alert_action(existing.get(key), scored["severity"])
        existing[key] = scored["severity"]
        bucket = engine._six_hour_bucket(ts)
        fingerprint = engine.alert_fingerprint(user_id, scored["severity"], top, bucket)
        record = {
            "user_id": user_id,
            "event_id": scored["event_id"],
            "severity": scored["severity"],
            "risk_score": scored["risk_score"],
            "top_families": sorted(set(top))[:3],
            "bucket": bucket,
            "fingerprint": fingerprint,
            "action": action,
        }
        found = next((a for a in alerts if a["_key"] == key), None)
        if found is None:
            record["_key"] = key
            alerts.append(record)
        else:
            record["_key"] = key
            record["action"] = "update"
            found.update(record)
    for a in alerts:
        a.pop("_key", None)
    return alerts

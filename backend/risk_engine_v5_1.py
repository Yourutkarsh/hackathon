"""Sentinel Shift V5.1 deterministic risk engine - FIXED build.
Changes vs. the broken upload:
 1. rule_detector(event, baseline, preliminary_signals=None) - Rule E uses prelim signals only.
 2. Rule A never falls back to UTC when timezone is missing (local-time signals become unavailable).
 3. Rule B does not manufacture a score when sensitivity is missing.
 4. rule_detector returns rule_score=None + rule_available=False when no rule had valid inputs.
 5. temporal_component accepts raw clusters OR precomputed summaries (Section 16 dual-form contract).
 6. sensitivity_component accepts resource_history= (separate trusted 30-day comparable history, Section 17).
 7. context_component validates start_utc/end_utc effective ranges.
 8. normalized_components respects rule_available / never treats fallback 0 as observed evidence.
 9. cluster_events enforces the 72-hour analysis horizon.
10. Alert dedup resolved per Section 21: fingerprint keeps severity, matching uses a severity-agnostic
    dedup key so WATCH/ELEVATED -> HIGH/CRITICAL escalations UPDATE the existing alert.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

EPSILON = 1e-6
DEFAULT_WEIGHTS = {
    "behavioral_anomaly": 0.45,
    "temporal_correlation": 0.25,
    "sensitivity": 0.15,
    "novelty": 0.15,
    "context_adjustment": 0.15,
}
POSITIVE_WEIGHT_SUM = 1.00
SEVERITY_BANDS = (
    (0.0, 30.0, "NORMAL"),
    (30.0, 50.0, "WATCH"),
    (50.0, 70.0, "ELEVATED"),
    (70.0, 85.0, "HIGH"),
    (85.0, 100.0, "CRITICAL"),
)
SEVERITY_RANK = {label: i for i, (_, _, label) in enumerate(SEVERITY_BANDS)}
SENSITIVITY_SCORE = {"LOW": 0.0, "MEDIUM": 25.0, "HIGH": 75.0, "CRITICAL": 100.0}
CONTEXT_MULTIPLIER = {"LOW": 0.25, "MEDIUM": 0.60, "HIGH": 1.00}
NOVELTY_FAMILIES = (
    "LOCATION_NOVELTY",
    "DEVICE_NOVELTY",
    "APPLICATION_NOVELTY",
    "RESOURCE_NOVELTY",
)
ACTIVE_FAMILY_THRESHOLD = 50.0  # Section 16 qualifying threshold; reused for "active" families.


def clip100(value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(100.0, value))


def percentile_rank(x: float, baseline: Sequence[float]) -> Optional[float]:
    """Inclusive percentile: count(v <= x) / N * 100. None when unavailable."""
    cleaned = [float(v) for v in baseline if math.isfinite(float(v))]
    if not cleaned or not math.isfinite(float(x)):
        return None
    n = len(cleaned)
    return (sum(1 for v in cleaned if v <= float(x)) / n) * 100.0


def robust_statistical_score(x: float, baseline: Sequence[float]) -> Optional[float]:
    """Exact V5 robust-statistics score, including mandatory MAD=0 fallback. None = not_available."""
    cleaned = [float(v) for v in baseline if math.isfinite(float(v))]
    if not cleaned or not math.isfinite(float(x)):
        return None
    arr = np.asarray(cleaned, dtype=float)
    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median)))
    if mad > 0:
        robust_z = abs(float(x) - median) / max(mad * 1.4826, EPSILON)
        return clip100((robust_z / 6.0) * 100.0)
    if float(x) == median:
        return 0.0
    p = percentile_rank(float(x), cleaned)
    if p is None:
        return None
    p /= 100.0
    two_sided_extremeness = 2.0 * abs(p - 0.5)
    return clip100(two_sided_extremeness * 100.0)


def _minute_of_day(timestamp_utc: str, timezone_name: Optional[str] = None) -> Optional[int]:
    """Local minute-of-day. Returns None when timezone is missing/invalid - never guess (Section 10.3)."""
    if not timezone_name:
        return None
    try:
        dt = datetime.fromisoformat(str(timestamp_utc).replace("Z", "+00:00"))
    except ValueError:
        return None
    try:
        from zoneinfo import ZoneInfo
        dt = dt.astimezone(ZoneInfo(str(timezone_name)))
    except Exception:
        return None
    return dt.hour * 60 + dt.minute


def _parse_ts(value: Any) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _distance_outside_band(minute: int, start: int, end: int) -> int:
    """Minutes outside an inclusive circular daily activity band."""
    start %= 1440
    end %= 1440
    if start <= end:
        if start <= minute <= end:
            return 0
        return min((start - minute) % 1440, (minute - end) % 1440)
    if minute >= start or minute <= end:
        return 0
    return min(start - minute, minute - end)


def rule_detector(event: Mapping[str, Any], baseline: Mapping[str, Any],
                  preliminary_signals: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Deterministic Rules A-E (Section 12/12.1).

    Rule E consumes ONLY `preliminary_signals` - it never reads event['signals'].
    rule_score is None (and rule_available False) when no rule had valid inputs;
    a missing input never manufactures a score.
    """
    scores: Dict[str, float] = {}
    fired: List[str] = []

    # Rule A: linear after-hours deviation, 0 at band edge, 100 at >=180 minutes outside.
    # Local time only; unavailable (skipped) when timezone is missing - no UTC guessing.
    active_start = baseline.get("active_start_minute")
    active_end = baseline.get("active_end_minute")
    minute = _minute_of_day(event.get("timestamp_utc", ""), event.get("user_timezone"))
    if minute is not None and active_start is not None and active_end is not None:
        outside = _distance_outside_band(minute, int(active_start), int(active_end))
        rule_a = clip100((outside / 180.0) * 100.0)
        scores["RULE_A_AFTER_HOURS"] = rule_a
        if rule_a > 0:
            fired.append("TIME_DEVIATION")

    # Rule B: first-seen resource family with sensitivity tiers. Missing sensitivity -> no score.
    family = str(event.get("resource_family") or "__UNKNOWN__")
    seen = set(str(x) for x in (baseline.get("resource_families") or []))
    sensitivity = event.get("sensitivity")
    if family != "__UNKNOWN__" and family not in seen and sensitivity is not None:
        tier = SENSITIVITY_SCORE.get(str(sensitivity).upper())
        if tier is not None:
            scores["RULE_B_NOVEL_SENSITIVE_RESOURCE"] = {100.0: 100.0, 75.0: 100.0,
                                                         25.0: 60.0, 0.0: 30.0}[tier]
            fired.append("RESOURCE_NOVELTY")

    # Rule C: larger robust score between data_mb and file_count.
    candidates = []
    data_baseline = baseline.get("data_mb_baseline") or []
    file_baseline = baseline.get("file_count_baseline") or []
    if event.get("data_mb") is not None and data_baseline:
        s = robust_statistical_score(float(event["data_mb"]), data_baseline)
        if s is not None:
            candidates.append(s)
    if event.get("file_count") is not None and file_baseline:
        s = robust_statistical_score(float(event["file_count"]), file_baseline)
        if s is not None:
            candidates.append(s)
    if candidates:
        scores["RULE_C_VOLUME_SPIKE"] = max(candidates)
        if scores["RULE_C_VOLUME_SPIKE"] >= ACTIVE_FAMILY_THRESHOLD:
            fired.append("VOLUME_SPIKE")

    # Rule D: rolling 30-minute count vs trusted prior rolling-count baseline.
    burst_count = event.get("rolling_30m_event_count")
    burst_baseline = baseline.get("rolling_30m_count_baseline") or []
    if burst_count is not None and burst_baseline:
        s = robust_statistical_score(float(burst_count), burst_baseline)
        if s is not None:
            scores["RULE_D_RAPID_BURST"] = s
            if s >= ACTIVE_FAMILY_THRESHOLD:
                fired.append("VELOCITY_CHANGE")

    # Rule E: >=3 preliminary signal families with score >= 70 -> exactly 25 rule points.
    # Uses ONLY preliminary_signals (pre-merge). Never event['signals'].
    if preliminary_signals:
        high_conf_families = set()
        for fam, value in preliminary_signals.items():
            try:
                v = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(v) and clip100(v) >= 70.0:
                high_conf_families.add(str(fam))
        if len(high_conf_families) >= 3:
            scores["RULE_E_MULTI_FAMILY"] = 25.0
            fired.extend(sorted(high_conf_families))

    rule_available = bool(scores)
    return {
        "rule_score": clip100(max(scores.values())) if rule_available else None,
        "rule_scores": scores,
        "fired_families": sorted(set(fired)),
        "rule_available": rule_available,
    }


def iforest_score(raw_anomaly_score: float, q95: float, q99: float) -> float:
    """Map higher-is-more-anomalous Isolation Forest score to [0,100] with q99==q95 fallback."""
    if not all(math.isfinite(float(v)) for v in (raw_anomaly_score, q95, q99)):
        return 0.0
    scale = max(float(q99) - float(q95), EPSILON)
    return clip100(((float(raw_anomaly_score) - float(q95)) / scale) * 100.0)


def _cluster_stats(cluster: Any) -> Tuple[int, int]:
    if isinstance(cluster, Mapping):
        return max(0, int(cluster.get("event_count", 0))), \
               max(0, int(cluster.get("distinct_signal_families", 0)))
    # Raw cluster: list/sequence of events.
    events = list(cluster)
    families = set()
    for e in events:
        for fam, score in (e.get("signals") or {}).items():
            try:
                if score is not None and math.isfinite(float(score)) and float(score) >= ACTIVE_FAMILY_THRESHOLD:
                    families.add(str(fam))
            except (TypeError, ValueError):
                continue
    return len(events), len(families)


def temporal_component(clusters: Sequence[Any]) -> float:
    """Bounded multi-cluster persistence/diversity score.

    Accepts EITHER raw event clusters (List[List[Event]]) OR precomputed
    cluster-summary mappings; both produce the same number (Section 16).
    """
    total = 0.0
    for c in clusters:
        n, k = _cluster_stats(c)
        persistence = min(math.log1p(n) / math.log1p(5), 1.0)
        diversity = min(k / 5.0, 1.0)
        total += persistence * diversity
    return clip100(100.0 * min(total / 3.0, 1.0))


def novelty_from_frequency(count: int, n: int) -> float:
    """Exact V5 smoothed categorical rarity score."""
    if n <= 0:
        return 100.0
    p = (max(0, int(count)) + 1.0) / (n + 1.0)
    return clip100((-math.log(p) / math.log(n + 1.0)) * 100.0)


def novelty_component(events: Sequence[Mapping[str, Any]]) -> float:
    best = 0.0
    for event in events:
        signals = event.get("signals") or {}
        present: List[float] = []
        for family in NOVELTY_FAMILIES:
            value = signals.get(family)
            if value is None:
                continue
            try:
                value_f = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(value_f):
                present.append(clip100(value_f))
        if present:
            best = max(best, sum(present) / len(present))
    return clip100(best)


def sensitivity_component(
    events: Sequence[Mapping[str, Any]],
    resource_history: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Tuple[float, bool]:
    """Max sensitivity elevation over STRICTLY prior comparable-resource history (Section 17).

    `resource_history` is the separate trusted 30-day comparable-resource history;
    scored `events` are processed after it. Concurrent timestamps (t_prior == t_current)
    never serve as one another's history.
    """
    history: Dict[str, List[Tuple[str, float]]] = {}
    for h in (resource_history or []):
        fam = str(h.get("resource_family") or "__UNKNOWN__")
        ts = str(h.get("timestamp_utc", ""))
        score = SENSITIVITY_SCORE.get(str(h.get("sensitivity", "LOW")).upper(), 0.0)
        history.setdefault(fam, []).append((ts, score))

    ordered = sorted(events, key=lambda e: (
        str(e.get("timestamp_utc", "")),
        str(e.get("user_id", "")),
        str(e.get("event_id", "")),
    ))
    best = 0.0
    has_comparable_history = False
    for event in ordered:
        family = str(event.get("resource_family") or "__UNKNOWN__")
        current_ts = str(event.get("timestamp_utc", ""))
        current = SENSITIVITY_SCORE.get(str(event.get("sensitivity", "LOW")).upper(), 0.0)
        prior_scores = [score for ts, score in history.get(family, []) if ts < current_ts]
        if prior_scores:
            has_comparable_history = True
            baseline_mean = sum(prior_scores) / len(prior_scores)
            best = max(best, clip100(current - baseline_mean))
        history.setdefault(family, []).append((current_ts, current))
    return clip100(best), has_comparable_history


def context_component(
    contexts: Sequence[Mapping[str, Any]],
    active_families: Iterable[str],
    now_utc: Optional[Any] = None,
) -> Tuple[float, bool]:
    """Bounded context discount; applies only to targeted ACTIVE families, inside effective time range.

    `now_utc` may be an ISO string or datetime; when omitted, range checks are skipped only
    if the record carries no start/end (stale-record enforcement happens at load time otherwise).
    """
    active_set = {str(f) for f in active_families}
    now_dt = _parse_ts(now_utc) if now_utc is not None else None
    total = 0.0
    applicable = False
    for ctx in contexts:
        target_families = {str(f) for f in (ctx.get("affected_signal_families") or [])}
        if not target_families.intersection(active_set):
            continue
        start = _parse_ts(ctx.get("start_utc")) if ctx.get("start_utc") else None
        end = _parse_ts(ctx.get("end_utc")) if ctx.get("end_utc") else None
        if now_dt is not None:
            if start is not None and now_dt < start:
                continue
            if end is not None and now_dt > end:
                continue
        raw_value = ctx.get("raw_reduction_points", ctx.get("applied_reduction", 0.0))
        try:
            raw = clip100(float(raw_value))
        except (TypeError, ValueError):
            continue
        confidence = str(ctx.get("confidence", "LOW")).upper()
        total += raw * CONTEXT_MULTIPLIER.get(confidence, 0.25)
        applicable = True
    return clip100(total), applicable


@dataclass(frozen=True)
class RiskComponents:
    values: Dict[str, float]
    availability: Dict[str, bool]
    active_signal_families: List[str]


def normalized_components(
    events: Sequence[Mapping[str, Any]],
    clusters: Sequence[Any],
    contexts: Sequence[Mapping[str, Any]],
    *,
    iforest_q95: Optional[float] = None,
    iforest_q99: Optional[float] = None,
    resource_history: Optional[Sequence[Mapping[str, Any]]] = None,
    now_utc: Optional[Any] = None,
) -> RiskComponents:
    behavioral_candidates: List[float] = []
    active_families = set()

    for event in events:
        signals = event.get("signals") or {}
        for family, score in signals.items():
            if score is not None:
                try:
                    if clip100(float(score)) >= ACTIVE_FAMILY_THRESHOLD:
                        active_families.add(str(family))
                except (TypeError, ValueError):
                    pass
        statistical = event.get("statistical_score")
        rule = event.get("rule_score")
        rule_available = event.get("rule_available", rule is not None)
        if statistical is not None and math.isfinite(float(statistical)):
            behavioral_candidates.append(clip100(float(statistical)))
        if rule is not None and rule_available and math.isfinite(float(rule)):
            behavioral_candidates.append(clip100(float(rule)))
        if (
            iforest_q95 is not None
            and iforest_q99 is not None
            and event.get("iforest_anomaly_score") is not None
            and math.isfinite(float(event["iforest_anomaly_score"]))
        ):
            behavioral_candidates.append(
                iforest_score(float(event["iforest_anomaly_score"]), iforest_q95, iforest_q99)
            )

    behavioral = max(behavioral_candidates) if behavioral_candidates else 0.0
    behavioral_available = bool(behavioral_candidates)

    novelty_available = any(
        any((event.get("signals") or {}).get(f) is not None for f in NOVELTY_FAMILIES)
        for event in events
    )
    novelty = novelty_component(events) if novelty_available else 0.0

    sensitivity, sensitivity_available = sensitivity_component(events, resource_history=resource_history)
    temporal_available = len(clusters) > 0
    temporal = temporal_component(clusters) if temporal_available else 0.0

    context, context_available = context_component(contexts, active_families, now_utc=now_utc)

    return RiskComponents(
        values={
            "behavioral_anomaly": clip100(behavioral),
            "temporal_correlation": clip100(temporal),
            "sensitivity": clip100(sensitivity),
            "novelty": clip100(novelty),
            "context_adjustment": clip100(context),
        },
        availability={
            "behavioral_anomaly": behavioral_available,
            "temporal_correlation": temporal_available,
            "sensitivity": sensitivity_available,
            "novelty": novelty_available,
            "context_adjustment": context_available,
        },
        active_signal_families=sorted(active_families),
    )


def compute_final_risk_score(components: Mapping[str, float] | RiskComponents) -> float:
    values = components.values if isinstance(components, RiskComponents) else components
    raw_risk = (
        DEFAULT_WEIGHTS["behavioral_anomaly"] * clip100(float(values.get("behavioral_anomaly", 0.0)))
        + DEFAULT_WEIGHTS["temporal_correlation"] * clip100(float(values.get("temporal_correlation", 0.0)))
        + DEFAULT_WEIGHTS["sensitivity"] * clip100(float(values.get("sensitivity", 0.0)))
        + DEFAULT_WEIGHTS["novelty"] * clip100(float(values.get("novelty", 0.0)))
        - DEFAULT_WEIGHTS["context_adjustment"] * clip100(float(values.get("context_adjustment", 0.0)))
    )
    return round(max(0.0, min(100.0, raw_risk)), 2)


def severity_for_score(score: float) -> str:
    score = clip100(score)
    for low, high, label in SEVERITY_BANDS:
        if low <= score < high:
            return label
    return "CRITICAL"


def detection(score: float, threshold: float) -> bool:
    return float(score) >= float(threshold)


def _six_hour_bucket(ts: Any) -> str:
    dt = _parse_ts(ts)
    if dt is None:
        return "unknown"
    bucket = dt.hour // 6
    return f"{dt.date().isoformat()}T{bucket*6:02d}:00Z"


def alert_fingerprint(user_id: str, severity: str, top_families: Sequence[str], bucket_id: str) -> str:
    """Spec Section 21 fingerprint: user + severity_band + top-3 families + 6-hour bucket."""
    families = sorted(set(str(x) for x in top_families))[:3]
    return f"{user_id}|{severity}|{','.join(families)}|{bucket_id}"


def dedup_key(user_id: str, top_families: Sequence[str], timestamp_utc: Any) -> str:
    """Severity-AGNOSTIC match key. Resolves the Section 21 contradiction: escalation
    (WATCH/ELEVATED -> HIGH/CRITICAL) matches the existing alert via this key and forces
    an in-place update instead of creating a second alert."""
    families = sorted(set(str(x) for x in top_families))[:3]
    return f"{user_id}|{','.join(families)}|{_six_hour_bucket(timestamp_utc)}"


def resolve_alert_action(existing_severity: Optional[str], new_severity: str) -> str:
    """'update' in place (including mandatory escalation) or 'create' a new alert."""
    if existing_severity is None:
        return "create"
    if SEVERITY_RANK.get(new_severity, 0) > SEVERITY_RANK.get(existing_severity, 0):
        return "update"  # mandatory escalation update
    return "update"


def cluster_events(events: Sequence[Mapping[str, Any]], gap_minutes: int = 30,
                   horizon_hours: int = 72) -> List[List[Mapping[str, Any]]]:
    """Cluster qualifying events (>=1 family score >= 50).

    An exact gap of `gap_minutes` starts a new cluster (Section 16, inclusive boundary).
    Events older than `horizon_hours` before the newest qualifying event are excluded
    from clustering (the 72-hour analysis horizon is enforced here).
    """
    qualifying = []
    for e in events:
        scores = e.get("signals") or {}
        if any(float(v) >= ACTIVE_FAMILY_THRESHOLD for v in scores.values() if v is not None):
            qualifying.append(e)
    qualifying = sorted(qualifying, key=lambda e: (
        str(e.get("timestamp_utc", "")),
        str(e.get("user_id", "")),
        str(e.get("event_id", "")),
    ))
    if not qualifying:
        return []
    newest = _parse_ts(qualifying[-1].get("timestamp_utc"))
    if newest is not None:
        cutoff = newest - timedelta(hours=horizon_hours)
        qualifying = [e for e in qualifying
                      if (t := _parse_ts(e.get("timestamp_utc"))) is not None and t >= cutoff]
    clusters: List[List[Mapping[str, Any]]] = []
    previous_dt: Optional[datetime] = None
    for e in qualifying:
        ts = _parse_ts(e["timestamp_utc"])
        if ts is None:
            continue
        if previous_dt is None or (ts - previous_dt).total_seconds() >= gap_minutes * 60:
            clusters.append([e])
        else:
            clusters[-1].append(e)
        previous_dt = ts
    return clusters


def cluster_summaries(clusters: Sequence[Sequence[Mapping[str, Any]]]) -> List[Dict[str, Any]]:
    out = []
    for idx, cluster in enumerate(clusters, start=1):
        families = set()
        ids = []
        for e in cluster:
            ids.append(str(e.get("event_id")))
            for fam, score in (e.get("signals") or {}).items():
                if score is not None and float(score) >= ACTIVE_FAMILY_THRESHOLD:
                    families.add(str(fam))
        out.append({
            "cluster_id": idx,
            "event_count": len(cluster),
            "distinct_signal_families": len(families),
            "event_ids": sorted(ids),
        })
    return out


def confidence_score(*, baseline_ready: bool, timezone_available: bool,
                     iforest_available: bool, sensitivity_history_available: bool,
                     required_missing_fraction: float) -> int:
    score = 100
    if not timezone_available:
        score -= 10
    if not baseline_ready:
        score -= 15
    if not iforest_available:
        score -= 5
    if not sensitivity_history_available:
        score -= 5
    if required_missing_fraction > 0.30:
        score -= 15
    return int(max(0, min(100, score)))


__all__ = [
    "clip100", "percentile_rank", "robust_statistical_score", "iforest_score", "DEFAULT_WEIGHTS",
    "POSITIVE_WEIGHT_SUM", "ACTIVE_FAMILY_THRESHOLD",
    "temporal_component", "novelty_from_frequency", "novelty_component",
    "sensitivity_component", "context_component", "RiskComponents", "normalized_components",
    "rule_detector", "compute_final_risk_score", "severity_for_score", "detection",
    "alert_fingerprint", "dedup_key", "resolve_alert_action",
    "cluster_events", "cluster_summaries", "confidence_score",
]

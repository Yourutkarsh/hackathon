"""Isolation Forest adapter (``iforest-v1``) for Sentinel Shift V5.1.

This module is the ONLY place real ``scikit-learn`` Isolation Forest scoring
happens. It never touches the immutable ``risk_engine_v5_1`` formulas: it only
produces a raw anomaly score plus the q95/q99 quantiles required by the engine's
own ``iforest_score`` mapping function.

Guarantees (compliance addendum):
  * **Chronological trusted-history training.** A per-user model is trained on
    that user's *strictly prior* trusted events (no current/future leakage).
  * **Documented minimum-history fallback.** At least ``MIN_HISTORY`` (= 10)
    training events are required. Below that, the adapter falls back to a
    **population** model trained only on *other* users' trusted events.
  * **No fabrication.** If neither the user nor the population has a valid
    training set, availability stays ``False`` and no score is produced.
  * **q95/q99 handling.** Quantiles are computed from the training anomaly-score
    distribution; a constant-feature population yields q99 == q95 and the engine's
    deterministic fallback applies.
  * **Determinism.** ``random_state`` is locked and identical training matrices
    reuse one fitted model (LRU-cached), so results are reproducible.
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
from sklearn.ensemble import IsolationForest

import risk_engine_v5_1 as engine

MODEL_NAME = "iforest-v1"
MODEL_VERSION = "iforest-v1"
MIN_HISTORY = 10
N_ESTIMATORS = 100
RANDOM_STATE = 42

FEATURE_NAMES = (
    "data_mb",
    "file_count",
    "minute_of_day",
    "sensitivity_score",
    "novelty_mean",
    "signal_count",
)

_SENSITIVITY = {"LOW": 0.0, "MEDIUM": 25.0, "HIGH": 75.0, "CRITICAL": 100.0}
_NOVELTY_FAMILIES = (
    "LOCATION_NOVELTY",
    "DEVICE_NOVELTY",
    "APPLICATION_NOVELTY",
    "RESOURCE_NOVELTY",
)


def _num(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        f = float(value)
        if math.isfinite(f):
            return f
    return default


def _sensitivity_score(value: Any) -> float:
    return _SENSITIVITY.get(str(value or "LOW").upper(), 0.0)


@lru_cache(maxsize=20000)
def _vector_from_parts(
    timestamp_utc: str,
    timezone_name: Any,
    data_mb: Any,
    file_count: Any,
    sensitivity: Any,
    signals: Tuple[Tuple[str, float], ...],
) -> Tuple[float, ...]:
    """Deterministic numeric feature vector (memoized; missing -> neutral).

    Memoization matters: the population fallback extracts features for every
    trusted event on every scored event, and the local-time zone math is the
    dominant cost. Caching keeps evaluation fast while remaining deterministic.
    """
    signal_map = dict(signals)
    novelty = [
        signal_map[f]
        for f in _NOVELTY_FAMILIES
        if f in signal_map and math.isfinite(signal_map[f])
    ]
    novelty_mean = sum(novelty) / len(novelty) if novelty else 0.0
    minute = engine._minute_of_day(timestamp_utc, timezone_name)  # read-only engine helper
    return (
        _num(data_mb),
        _num(file_count),
        float(minute) if minute is not None else -1.0,
        _sensitivity_score(sensitivity),
        float(novelty_mean),
        float(len(novelty)),
    )


def feature_vector(event: Mapping[str, Any]) -> Tuple[float, ...]:
    """Deterministic numeric feature vector for one event (missing -> neutral)."""
    signals = event.get("signals") or {}
    signal_key = tuple(sorted(
        (str(k), float(v))
        for k, v in signals.items()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    ))
    return _vector_from_parts(
        str(event.get("timestamp_utc") or ""),
        event.get("user_timezone"),
        event.get("data_mb"),
        event.get("file_count"),
        event.get("sensitivity"),
        signal_key,
    )


@lru_cache(maxsize=256)
def _fit_cached(
    matrix: Tuple[Tuple[float, ...], ...],
) -> Tuple[IsolationForest, float, float]:
    """Fit (and cache) an Isolation Forest; return model + q95/q99 quantiles.

    Cached on the exact training matrix so identical populations are fitted once
    (keeps evaluation fast and fully reproducible).
    """
    arr = np.asarray(matrix, dtype=float)
    model = IsolationForest(
        n_estimators=N_ESTIMATORS,
        random_state=RANDOM_STATE,
        contamination="auto",
    )
    model.fit(arr)
    train_raw = (-model.score_samples(arr)).tolist()
    q95 = float(np.percentile(train_raw, 95))
    q99 = float(np.percentile(train_raw, 99))
    return model, q95, q99


def _raw_score(model: IsolationForest, vector: Tuple[float, ...]) -> float:
    return float(-model.score_samples(np.asarray([vector], dtype=float))[0])


# Population (user_id, feature-vector) rows, cached per population signature so
# the fallback pool is materialized once per evaluation instead of once per event.
_POPULATION_ROWS_CACHE: Dict[Tuple[str, ...], Tuple[Tuple[Any, Tuple[float, ...]], ...]] = {}


def _population_rows(
    population_events: Sequence[Mapping[str, Any]],
) -> Tuple[Tuple[Any, Tuple[float, ...]], ...]:
    key = tuple(str(e.get("event_id")) for e in population_events)
    rows = _POPULATION_ROWS_CACHE.get(key)
    if rows is None:
        rows = tuple(
            (e.get("user_id"), feature_vector(e))
            for e in population_events
            if not e.get("quarantined")
        )
        _POPULATION_ROWS_CACHE.clear()
        _POPULATION_ROWS_CACHE[key] = rows
    return rows


def _unavailable(reason: str, *, user_train: int, population_train: int) -> Dict[str, Any]:
    return {
        "available": False,
        "model": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "source": None,
        "population_fallback": False,
        "training_count": user_train,
        "population_training_count": population_train,
        "min_history": MIN_HISTORY,
        "n_estimators": N_ESTIMATORS,
        "random_state": RANDOM_STATE,
        "q95": None,
        "q99": None,
        "raw_score": None,
        "scaled_score": None,
        "fallback_reason": reason,
    }


def score_event(
    prior_events: Sequence[Mapping[str, Any]],
    target_event: Mapping[str, Any],
    population_events: Optional[Sequence[Mapping[str, Any]]] = None,
    *,
    min_history: int = MIN_HISTORY,
) -> Dict[str, Any]:
    """Score ``target_event`` with an Isolation Forest trained on prior history.

    ``population_events`` must be the full trusted population; the target user's
    own events are filtered out here so the fallback never leaks the target.
    """
    user_train = [
        feature_vector(e) for e in prior_events if not e.get("quarantined")
    ]
    target_user = target_event.get("user_id")
    pop_train = [
        vector
        for user_id, vector in _population_rows(population_events or [])
        if user_id != target_user
    ]

    if len(user_train) >= min_history:
        source, training, fallback = "user", user_train, None
    elif len(pop_train) >= min_history:
        source, training, fallback = "population", pop_train, "insufficient_user_history"
    else:
        return _unavailable(
            "insufficient_training_population",
            user_train=len(user_train),
            population_train=len(pop_train),
        )

    model, q95, q99 = _fit_cached(tuple(training))
    raw = _raw_score(model, feature_vector(target_event))
    scaled = engine.iforest_score(raw, q95, q99)
    return {
        "available": True,
        "model": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "source": source,
        "population_fallback": source == "population",
        "training_count": len(training),
        "population_training_count": len(pop_train),
        "min_history": min_history,
        "n_estimators": N_ESTIMATORS,
        "random_state": RANDOM_STATE,
        "q95": q95,
        "q99": q99,
        "raw_score": raw,
        "scaled_score": scaled,
        "fallback_reason": fallback,
        "feature_names": list(FEATURE_NAMES),
    }


def clear_cache() -> None:
    """Drop cached models and feature vectors (used by tests / after a reset)."""
    _fit_cached.cache_clear()
    _vector_from_parts.cache_clear()
    _POPULATION_ROWS_CACHE.clear()


def model_metadata() -> Dict[str, Any]:
    """Static, provider-agnostic model metadata for API responses."""
    return {
        "model": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "algorithm": "sklearn.ensemble.IsolationForest",
        "min_history": MIN_HISTORY,
        "n_estimators": N_ESTIMATORS,
        "random_state": RANDOM_STATE,
        "features": list(FEATURE_NAMES),
        "provider": "local-scikit-learn",
    }


__all__ = [
    "MODEL_NAME",
    "MODEL_VERSION",
    "MIN_HISTORY",
    "N_ESTIMATORS",
    "RANDOM_STATE",
    "FEATURE_NAMES",
    "feature_vector",
    "score_event",
    "model_metadata",
    "clear_cache",
]

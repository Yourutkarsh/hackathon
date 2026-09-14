"""Informational calibration sweep (V5.1 compliance hardening).

A chronological 60/20/20 split (train / calibration / locked test) over the
scored trusted population. A detection threshold is selected on the calibration
slice under an FPR constraint with fully deterministic tie-breaks, then scored
ONCE on the locked test slice.

Guarantees:
  * **Chronological & locked.** Records are sorted by
    ``(timestamp_utc, user_id, event_id)`` and the test slice is the last 20%;
    it is never used to choose the threshold.
  * **Deterministic.** Candidate thresholds are the sorted unique observed
    scores; ties break by (recall desc, precision desc, threshold desc, index asc).
  * **Reporting-only.** The selected threshold is NEVER written back into global
    detection (`mutates_global_detection: False`). The engine's severity bands
    stay the single source of truth for alerting.
  * **Empty-slice safe.** Missing calibration/test slices fall back to the spec
    threshold and report zeroed metrics instead of raising.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from .lifecycle import SPEC_DETECTION_THRESHOLD

TARGET_FPR = 0.10
TRAIN_FRACTION = 0.6
CALIBRATION_FRACTION = 0.2


def _sort_key(record: Mapping[str, Any]) -> Tuple[str, str, str]:
    return (
        str(record.get("timestamp_utc") or ""),
        str(record.get("user_id") or ""),
        str(record.get("event_id") or ""),
    )


def chronological_split(
    records: Sequence[Mapping[str, Any]],
) -> Tuple[List[Mapping[str, Any]], List[Mapping[str, Any]], List[Mapping[str, Any]]]:
    """60/20/20 chronological split (floored boundaries, remainder -> test)."""
    ordered = sorted(records, key=_sort_key)
    n = len(ordered)
    n_train = int(n * TRAIN_FRACTION)
    n_cal = int(n * CALIBRATION_FRACTION)
    return ordered[:n_train], ordered[n_train:n_train + n_cal], ordered[n_train + n_cal:]


def confusion(
    records: Sequence[Mapping[str, Any]], threshold: float
) -> Dict[str, Any]:
    tp = fp = tn = fn = 0
    for r in records:
        detected = float(r.get("score", 0.0)) >= float(threshold)
        positive = bool(r.get("positive"))
        if detected and positive:
            tp += 1
        elif detected and not positive:
            fp += 1
        elif not detected and positive:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "threshold": round(float(threshold), 4),
        "n": len(records),
        "positives": sum(1 for r in records if r.get("positive")),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
    }


def select_threshold(
    calibration: Sequence[Mapping[str, Any]],
    *,
    target_fpr: float = TARGET_FPR,
    fallback_threshold: float = SPEC_DETECTION_THRESHOLD,
) -> Dict[str, Any]:
    """FPR-constrained threshold selection with deterministic tie-breaks."""
    scores = [float(r.get("score", 0.0)) for r in calibration]
    candidates = sorted(set(scores + [float(fallback_threshold)]))
    qualified: List[Tuple[float, Dict[str, Any], int]] = []
    for idx, threshold in enumerate(candidates):
        metrics = confusion(calibration, threshold)
        if metrics["false_positive_rate"] <= target_fpr:
            qualified.append((threshold, metrics, idx))

    if not qualified:
        metrics = confusion(calibration, fallback_threshold)
        return {
            "selected_threshold": round(float(fallback_threshold), 4),
            "fallback_used": True,
            "qualified_count": 0,
            "candidate_count": len(candidates),
            "selection_objective": "maximize recall s.t. calibration FPR <= target_fpr",
            "tie_break": "recall desc, precision desc, threshold desc, index asc",
            "calibration_at_threshold": metrics,
        }

    # max() is stable; the key makes every tie deterministic.
    threshold, metrics, _idx = max(
        qualified,
        key=lambda c: (c[1]["recall"], c[1]["precision"], c[0], -c[2]),
    )
    return {
        "selected_threshold": round(float(threshold), 4),
        "fallback_used": False,
        "qualified_count": len(qualified),
        "candidate_count": len(candidates),
        "selection_objective": "maximize recall s.t. calibration FPR <= target_fpr",
        "tie_break": "recall desc, precision desc, threshold desc, index asc",
        "calibration_at_threshold": metrics,
    }


def calibrate(
    records: Sequence[Mapping[str, Any]],
    *,
    target_fpr: float = TARGET_FPR,
    fallback_threshold: float = SPEC_DETECTION_THRESHOLD,
) -> Dict[str, Any]:
    """Run the full informational calibration sweep over scored records."""
    train, calibration, test = chronological_split(records)
    empty_slices = not calibration or not test
    selection = select_threshold(
        calibration,
        target_fpr=target_fpr,
        fallback_threshold=fallback_threshold,
    )
    selected = selection["selected_threshold"]
    return {
        "method": "chronological_fpr_constrained",
        "reporting_only": True,
        "mutates_global_detection": False,
        "split_ratio": "60/20/20",
        "split": {
            "total": len(records),
            "train": len(train),
            "calibration": len(calibration),
            "test": len(test),
        },
        "target_fpr": target_fpr,
        "empty_slices": empty_slices,
        "selected_threshold": selected,
        "fallback_used": selection["fallback_used"] or empty_slices,
        "fallback_threshold": round(float(fallback_threshold), 4),
        "candidate_count": selection["candidate_count"],
        "qualified_count": selection["qualified_count"],
        "selection_objective": selection["selection_objective"],
        "tie_break": selection["tie_break"],
        "train_metrics": confusion(train, selected),
        "calibration_metrics": selection["calibration_at_threshold"],
        "locked_test_metrics": confusion(test, selected),
        "note": (
            "Informational only: the selected threshold is reported and never "
            "applied to global detection or alerting."
        ),
    }


__all__ = [
    "TARGET_FPR",
    "chronological_split",
    "confusion",
    "select_threshold",
    "calibrate",
]

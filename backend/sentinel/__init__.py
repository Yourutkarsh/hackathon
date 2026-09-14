"""Sentinel Shift V5.1 - deterministic MongoDB persistence and scoring package.

This package provides:
  - Deterministic, immutable in-memory seed fixtures (synthetic population).
  - Structural validation with quarantine / incomplete-event rules.
  - A standalone, HTTP-independent ``reset_demo_db()`` reset module.
  - Engine integrity / import-contract helpers for the vendored, read-only
    ``risk_engine_v5_1.py``.
  - Compliance hardening (V5.1): detection thresholds + baseline lifecycle
    (``lifecycle``), the Isolation Forest adapter (``iforest``), and the
    informational calibration sweep (``calibration``).
"""
from .fixtures import (
    SEED_VERSION,
    ENGINE_VERSION,
    get_fixture,
    fixture_hash,
    build_baseline_for,
)
from .demo_db import (
    reset_demo_db,
    ensure_indexes,
    get_db,
    verify_engine_integrity,
    current_baseline_version,
    next_baseline_version,
    ENGINE_CHECKSUM,
)
from .lifecycle import (
    SPEC_DETECTION_THRESHOLD,
    SPEC_DETECTION_SEVERITIES,
    LEGACY_DETECTION_THRESHOLD,
    LEGACY_DETECTION_SEVERITIES,
    FLAGGED_SEVERITIES,
    baseline_state,
    baseline_lifecycle,
    detection_config,
)
from .iforest import MIN_HISTORY, MODEL_NAME, model_metadata as iforest_model_metadata
from .calibration import calibrate

__all__ = [
    "SEED_VERSION",
    "ENGINE_VERSION",
    "ENGINE_CHECKSUM",
    "get_fixture",
    "fixture_hash",
    "build_baseline_for",
    "reset_demo_db",
    "ensure_indexes",
    "get_db",
    "verify_engine_integrity",
    "current_baseline_version",
    "next_baseline_version",
    "SPEC_DETECTION_THRESHOLD",
    "SPEC_DETECTION_SEVERITIES",
    "LEGACY_DETECTION_THRESHOLD",
    "LEGACY_DETECTION_SEVERITIES",
    "FLAGGED_SEVERITIES",
    "baseline_state",
    "baseline_lifecycle",
    "detection_config",
    "MIN_HISTORY",
    "MODEL_NAME",
    "iforest_model_metadata",
    "calibrate",
]

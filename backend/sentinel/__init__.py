"""Sentinel Shift V5.1 - Phase 1 MongoDB persistence and deterministic fixtures.

This package provides:
  - Deterministic, immutable in-memory seed fixtures (10 synthetic users).
  - Structural validation with quarantine / incomplete-event rules.
  - A standalone, HTTP-independent ``reset_demo_db()`` reset module.
  - Engine integrity / import-contract helpers for the vendored, read-only
    ``risk_engine_v5_1.py``.

Phase 1 intentionally contains NO FastAPI routes and NO HTTP endpoints.
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
    ENGINE_CHECKSUM,
)

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
]

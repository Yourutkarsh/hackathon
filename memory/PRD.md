# Sentinel Shift V5.1 — Product Requirements & Progress

## Original Problem Statement
Phase 1 — deterministic MongoDB data foundation for Sentinel Shift V5.1. Vendor
the immutable `risk_engine_v5_1.py` read-only; build MongoDB collections, a
validated seed fixture (10 users incl. Rahul's exact Events 1–8 with the
`rahul-006` London/02:15 compound anomaly), a standalone `reset_demo_db()`
module (no HTTP), and a verification gate. NO FastAPI routes and NO React in
Phase 1.

## Architecture
- **Engine (immutable, read-only)**: `/app/backend/risk_engine_v5_1.py` — vendored
  unchanged, `chmod 444`. SHA-256 recorded in `sentinel/ENGINE_MANIFEST.json` and
  enforced by `sentinel.verify_engine_integrity()`.
- **Package** `/app/backend/sentinel/`:
  - `models.py` — `PyObjectId`, `BaseDocument` (`_id`<->`id`, `to_mongo`/`from_mongo`), domain docs.
  - `validation.py` — timestamp normalization + quarantine / incomplete classification.
  - `fixtures.py` — frozen in-memory seed (10 users, events, contexts) + stable `fixture_hash()`.
  - `demo_db.py` — `get_db`, `ensure_indexes`, `reset_demo_db()` (pymongo, bulk `insert_many`).
- **Verification**: `/app/backend/test_phase1_persistence.py` + untouched `test_v51_fixes.py`.
- MongoDB via `MONGO_URL`/`DB_NAME` env only. Collections: `users`, `events`,
  `contexts`, `demo_state`, `audit_records`.

## Core Requirements (static)
- UTC-normalized BSON datetimes + preserved original timestamp string (provenance).
- Compound index `{timestamp_utc:1, user_id:1, event_id:1}` + supporting indexes.
- `(timestamp_utc, user_id, event_id)` tie-breaking for all ordering.
- Malformed events → quarantined (excluded from trusted). Incomplete-but-valid → retained, partial eval.
- No current/future event may enter its own baseline. Audit records append-only; dismissal is workflow-only.
- Deterministic seed/reset: identical fixture hash + counts. Warm reset < 50 ms (warn-only).

## Implemented (2026-06)
- [x] Vendored immutable engine (read-only) + checksum/import contract recorded & verified.
- [x] 5 collections with compound + supporting indexes (idempotent `ensure_indexes`).
- [x] Frozen fixture: 10 users; Rahul Events 1–8; `rahul-006` E6 = London, United Kingdom,
      Europe/London, 02:15 local (01:15 UTC), Bengaluru baseline contrast.
- [x] Quarantine cases (invalid timestamp / negative volume / invalid required type) +
      incomplete cases (missing timezone, missing volume) with deterministic confidence penalty.
- [x] Standalone `reset_demo_db()` (bulk insert, no HTTP), `demo_state` metadata
      (seed version, fixture hash, reset time, engine version + checksum, counts).
- [x] Verification gate `test_phase1_persistence.py`: 39 checks pass; `test_v51_fixes.py` passes unchanged.
      Warm reset measured ~2.9 ms.

## Backlog
- **P0 (Phase 2)**: FastAPI endpoints incl. `POST /api/demo/reset`, event/query/scoring routes.
- **P1**: React frontend (dashboard, anomaly review, audit workflow).
- **P2**: Runtime scoring pipeline persisting audit_records via the engine.

## Next Tasks
- Phase 2: expose `reset_demo_db()` via `POST /api/demo/reset` (async motor wrapper) + read APIs.

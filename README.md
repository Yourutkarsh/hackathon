# Sentinel Shift V5.1 — SOC Insider-Threat & Anomaly Workspace

Sentinel Shift is a Security Operations Center (SOC) demo that scores user
activity for insider-threat / account-compromise anomalies using a **frozen,
immutable reference risk engine** (`backend/risk_engine_v5_1.py`). The backend
is strictly authoritative for all risk math; the React frontend only *displays*
backend-provided scores, components, availability flags and evidence.

The signature scenario: **Rahul (`rahul-006`)** performs a bulk export from
**London, United Kingdom at 02:15 AM** — a compound anomaly (new location +
off-hours + volume spike) contrasted against his normal **Bengaluru** business-
hours baseline, driving his risk to **ELEVATED**.

> **V5.1 compliance hardening.** This build aligns the app with the supplied
> compliance addendum: new scenario taxonomy, strict spec detection, a real
> Isolation Forest adapter, exact baseline lifecycle boundaries, an informational
> calibration sweep, assistant schema alignment, and revised ablation variants —
> **without modifying the immutable engine**.

## Architecture
```
backend/
  risk_engine_v5_1.py     # IMMUTABLE reference engine (checksum-locked, read-only)
  test_v51_fixes.py       # IMMUTABLE targeted engine tests (must pass unchanged)
  test_phase1_persistence.py  # Phase-1 verification gate
  test_v51_boundaries.py  # V5.1 boundary / fallback / scenario suite
  server.py               # FastAPI app (all routes under /api)
  sentinel/
    fixtures.py           # Frozen deterministic seed (population + scenarios + ground truth)
    validation.py         # Timestamp normalization, quarantine + incomplete rules
    scoring.py            # Engine wrapper (scoring, ablation, alert dedup) — no formulas duplicated
    iforest.py            # Isolation Forest adapter (iforest-v1) — chronological, fallback-safe
    lifecycle.py          # Detection thresholds + COLD/WARMING/READY baseline lifecycle
    calibration.py        # Informational chronological 60/20/20 calibration sweep
    demo_db.py            # Standalone reset_demo_db() + indexes + demo_state/baseline_version
    service.py            # DB orchestration for the API layer
    models.py             # Pydantic docs (PyObjectId / BaseDocument)
frontend/                 # React (CRA + craco) SOC Investigation Workspace
```

### Risk model (engine, summarized)
Final score = weighted sum of five components (weights in `DEFAULT_WEIGHTS`):
- **Behavioral Anomaly** (0.45) — max of Rule A–E, robust statistical, isolation-forest channels
- **Temporal Correlation** (0.25) — multi-cluster persistence × diversity
- **Sensitivity Elevation** (0.15) — elevation over strictly-prior comparable resource history
- **Novelty** (0.15) — categorical rarity across location/device/app/resource families
- **Context Adjustment** (0.15, **subtracted**) — targeted, time-valid approved-context discount

Severity bands: `NORMAL <30`, `WATCH 30–50`, `ELEVATED 50–70`, `HIGH 70–85`, `CRITICAL 85+`.

### Detection threshold decision (adopted)
The addendum mandates **strict spec detection at HIGH/CRITICAL (score ≥ 70)**.
This is the adopted default for evaluation reporting. The pre-existing
`ELEVATED+` (score ≥ 50) rule is retained **only** as a temporary
backward-compatible alias (`overall_legacy`, `detection_threshold_legacy`,
legacy alerts) so existing consumers keep working during migration.

**Rahul E6 is explicitly verified:** it scores **67.98 (ELEVATED)** — legacy
detected (≥ 50) but *below* the strict 70 bar. It therefore surfaces through the
legacy alert band and is disclosed here as a known, deliberate boundary rather
than hidden. `test_v51_boundaries.py` asserts this outcome directly.

### Scenario taxonomy (V5.1)
`SUDDEN_COMPROMISE` (Rahul/London), `GRADUAL_INSIDER`, `LEGITIMATE_TRAVEL`,
`ROLE_CHANGE`, **`PROJECT_CHANGE`** (an approved new resource family that
**settles** under a time-valid context), **`MIXED_CASE`** (explained evidence
that is context-discounted **plus** an independent anomaly the context must not
suppress), `BENIGN_LATE_WORKER`, and **`NORMAL`** (renamed from `BENIGN`;
`BENIGN` remains available as a legacy alias in the evaluation response).

### Isolation Forest adapter (`iforest-v1`)
- Trained on each user's **strictly-prior** trusted events; documented
  **minimum history of 10 events**.
- Below 10 events it falls back to a **population** model trained only on
  *other* users' events. If no valid training population exists, availability
  stays **false** and **no score is fabricated**.
- Uses the engine's own `iforest_score(raw, q95, q99)` mapping; q95/q99 are the
  training anomaly-score quantiles (constant features ⇒ q99 == q95 and the
  engine's deterministic fallback applies).
- `random_state=42`; identical training matrices reuse one fitted model.

### Baseline lifecycle
Exact, tested boundaries on a user's trusted history:
`COLD` (< 20 events) → `WARMING` (20–49 events, or ≥ 50 events with < 7 distinct
days) → `READY` (≥ 50 events **and** ≥ 7 distinct days). The demo-wide
`baseline_version` increments atomically on every reset and is persisted in
`demo_state`.

### Calibration sweep (informational)
`/evaluation` includes a chronological **60/20/20** split (train / calibration /
locked test). A threshold is selected on the calibration slice to maximize recall
subject to `FPR ≤ 0.10`, with deterministic tie-breaks (recall → precision →
threshold → index), then scored **once** on the locked test slice. Calibration is
**reporting-only**: `mutates_global_detection: false`, and empty slices fall back
to the spec threshold instead of raising.

### Data rules
- UTC-normalized BSON datetimes; original timestamp string preserved for provenance.
- Compound index `{timestamp_utc, user_id, event_id}` + supporting indexes.
- Malformed events (bad timestamp / negative volume / wrong required type) are **quarantined** and excluded from trusted processing.
- Incomplete-but-valid events are retained and scored partially with deterministic confidence penalties.
- **No current or future event may enter the baseline used for its own score.**
- `audit_records` are append-only; dismissal is a workflow flag only and never affects scoring.

## API (all under `/api`)
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Engine version/integrity, seed, demo cursor, `baseline_version`, detection policy, iforest metadata |
| POST | `/demo/reset` | Reseed demo collections; increments + returns `baseline_version`, metrics (hash, counts, ms) |
| POST | `/demo/next-event?force=false` | Advance scripted stream by 1 event; **pauses at the London anomaly** (pass `force=true` to continue) |
| GET | `/users` | Population summary + per-user baseline lifecycle state |
| GET | `/users/{id}` | User profile + baseline lifecycle + counts |
| GET | `/users/{id}/timeline` | Chronological events (with quarantine flags) |
| GET | `/users/{id}/evidence` | Top scored event + per-event evidence summaries |
| GET | `/users/{id}/alerts` | Deduplicated alerts (engine Section-21 dedup/escalation) |
| POST | `/investigate` | Full risk state: score, severity, 5 components + availability, confidence, channels, iforest metadata, ablation, detection, baseline lifecycle, evidence provenance |
| POST | `/assistant/chat` | Offline deterministic grounded Q&A (`recommended_investigation_steps`, `evidence_ids`, `signal_families`; legacy `recommended_steps`/`citations` retained; `used_llm:false`) |
| POST | `/audit/action` | Append-only analyst action (NOTE / ESCALATE / DISMISS); never mutates risk |
| GET | `/audit` | Read the append-only audit trail |
| GET | `/evaluation` | Strict-spec precision/recall/F1/FPR + legacy alias, revised ablation ladder, calibration sweep, per-scenario rollup |

## Running
Services are managed by supervisor (do not start uvicorn/yarn manually):
```
sudo supervisorctl restart backend
sudo supervisorctl restart frontend
```
Backend binds `0.0.0.0:8001` (routes prefixed `/api`); the frontend uses
`REACT_APP_BACKEND_URL`. MongoDB is configured via `MONGO_URL` / `DB_NAME`.

See [`PREVIEW.md`](./PREVIEW.md) for the full install / run / preview guide
(env keys, health checks, preview commands, and troubleshooting).

## Verification
```
cd backend
python test_v51_fixes.py          # immutable engine tests -> ALL_TARGETED_TESTS_PASSED
python test_phase1_persistence.py # Phase-1 gate: seed/reset/indexes/quarantine/anomaly
python test_v51_boundaries.py     # V5.1 boundaries/fallback/scenario -> ALL_V51_BOUNDARY_TESTS_PASSED
python test_api_routes.py         # end-to-end /api routes via FastAPI TestClient -> ALL_API_ROUTE_TESTS_PASSED
python test_sentinel_invariants.py # sentinel-guard invariants -> ALL_SENTINEL_INVARIANTS_SATISFIED
```

### sentinel-guard invariants
`test_sentinel_invariants.py` codifies the `/sentinel-guard` skill so the
non-negotiables are enforced by tests rather than by memory:
1. **Engine immutability** — `risk_engine_v5_1.py` checksum matches
   `ENGINE_MANIFEST.json`, the file is read-only, and `verify_engine_integrity()` is `True`.
2. **Zero temporal leakage** — every user baseline is swept and proven strictly
   prior (`[t - window, t)`) with no self/future/cross-user/quarantined entries.
3. **Read-only LLM separation** — the assistant is offline (`used_llm: false`),
   mirrors — never recomputes — the engine score/severity, and never labels a user
   as malicious.
4. **Deterministic reproducibility** — no RNG in `sentinel/`, `random_state=42`,
   stable fixture hash/counts, deterministic engine score and calibration
   selection, and a sub-50 ms warm reset (asserted against a real MongoDB;
   warn-only under the pure-Python simulator).
Manual flow: **Reset** → **Rahul E6** → **investigate** (severity, components,
baseline state, iforest availability/fallback, ablation, deterministic
recommendations) → run **Evaluation** (strict + legacy detection, ablation
ladder, calibration). Then verify `PROJECT_CHANGE` settles and `MIXED_CASE`
stays ELEVATED or higher.

## Limitations & deliberate decisions
- **No live external LLM.** The Evidence Assistant is deterministic and offline
  by design, so answers are fully reproducible and grounded in event fields.
- **Strict 70+ detection has a known boundary.** The flagship Rahul E6 compound
  anomaly scores 67.98 (ELEVATED): detected under the legacy alias, not under the
  strict spec threshold. This is intentional (strict spec) and disclosed, not hidden.
- **Isolation Forest is adapter-scoped.** `iforest-v1` is local scikit-learn with
  a locked seed; per-user models need ≥ 10 prior events, otherwise the population
  fallback applies and is flagged in the API.
- **Calibration is reporting-only** and cannot mutate the global detection
  threshold or alerting.
- The population is synthetic and seeded deterministically for demo reproducibility.
- `reset_demo_db()` targets < 50 ms on a warm local MongoDB and reports (does not hide)
  a slower reset.

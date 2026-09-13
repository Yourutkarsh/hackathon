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

## Architecture
```
backend/
  risk_engine_v5_1.py     # IMMUTABLE reference engine (chmod 444, checksum-locked)
  test_v51_fixes.py       # IMMUTABLE targeted engine tests (must pass unchanged)
  test_phase1_persistence.py  # Phase-1 verification gate
  server.py               # FastAPI app (all routes under /api)
  sentinel/
    fixtures.py           # Frozen deterministic seed (population + scenarios + ground truth)
    validation.py         # Timestamp normalization, quarantine + incomplete rules
    scoring.py            # Engine wrapper (scoring, ablation, alert dedup) — no formulas duplicated
    demo_db.py            # Standalone reset_demo_db() + indexes + demo_state metadata
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
Detection threshold for evaluation = severity **≥ ELEVATED**.

### Data rules
- UTC-normalized BSON datetimes; original timestamp string preserved for provenance.
- Compound index `{timestamp_utc, user_id, event_id}` + supporting indexes.
- Malformed events (bad timestamp / negative volume / wrong required type) are **quarantined** and excluded from trusted processing.
- Incomplete-but-valid events are retained and scored partially with deterministic confidence penalties.
- **No current or future event may enter the baseline used for its own score.**
- `audit_records` are append-only; dismissal is a workflow flag only and never affects scoring.

### Synthetic population & scenarios
~60 users, 30–60 day histories, 5–8 events each, labelled with ground truth:
`SUDDEN_COMPROMISE` (Rahul/London), `GRADUAL_INSIDER` (escalating after-hours →
device → sensitive → volume → multi), `LEGITIMATE_TRAVEL` (novel location covered
by a time-valid context), `ROLE_CHANGE` (approved new resource access),
`BENIGN_LATE_WORKER` (night shift — no off-hours false positive), and `BENIGN`.

## API (all under `/api`)
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Engine version/integrity, seed, demo cursor |
| POST | `/demo/reset` | Reseed demo collections; returns metrics (hash, counts, ms) |
| POST | `/demo/next-event?force=false` | Advance scripted stream by 1 event; **pauses at the London anomaly** (pass `force=true` to continue) |
| GET | `/users` | Population summary |
| GET | `/users/{id}` | User profile + baseline + counts |
| GET | `/users/{id}/timeline` | Chronological events (with quarantine flags) |
| GET | `/users/{id}/evidence` | Top scored event + per-event evidence summaries |
| GET | `/users/{id}/alerts` | Deduplicated alerts (engine Section-21 dedup/escalation) |
| POST | `/investigate` | Full risk state: score, severity, 5 components + availability, confidence, signals, clusters, evidence provenance |
| POST | `/assistant/chat` | Offline deterministic grounded Q&A (answer, key facts, uncertainties, recommended steps, citations; `used_llm:false`) |
| POST | `/audit/action` | Append-only analyst action (NOTE / ESCALATE / DISMISS); never mutates risk |
| GET | `/audit` | Read the append-only audit trail |
| GET | `/evaluation` | Precision / recall / F1 / FPR + **component-ablation table** + per-scenario rollup |

## Running
Services are managed by supervisor (do not start uvicorn/yarn manually):
```
sudo supervisorctl restart backend
sudo supervisorctl restart frontend
```
Backend binds `0.0.0.0:8001` (routes prefixed `/api`); the frontend uses
`REACT_APP_BACKEND_URL`. MongoDB is configured via `MONGO_URL` / `DB_NAME`.

## Verification
```
cd backend
python test_v51_fixes.py          # immutable engine tests -> ALL_TARGETED_TESTS_PASSED
python test_phase1_persistence.py # Phase-1 gate: seed/reset/indexes/quarantine/anomaly
```

## Limitations
- The Evidence Assistant is **deterministic and offline** (no external LLM key required)
  by design, so answers are fully reproducible and grounded in event fields.
- The population is synthetic and seeded deterministically for demo reproducibility.
- `reset_demo_db()` targets < 50 ms on a warm local MongoDB and reports (does not hide)
  a slower reset.

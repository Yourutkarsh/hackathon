# Preview Guide — Sentinel Shift V5.1

How to install, run, and preview this project. This is **not** a single-server
SPA: it is a React dev server **plus** a FastAPI backend **plus** MongoDB, so
"the preview" is the frontend and the API runs alongside it.

> **Workspace note:** the Freebuff preview/deploy CLIs (`freebuff-preview`,
> `freebuff-deploy`, `freebuff-env`) are **not installed in this workspace**
> (nothing on `PATH`), so the `set-install` / `set` / `set-build` commands below
> could not be saved from here. Apply them from the Freebuff preview UI (or a
> workspace where the CLI exists). Everything else in this guide was verified
> against the repo.

---

## 1. What runs

| Piece | Tech | Default port | Entry point |
|---|---|---|---|
| Frontend (preview target) | React 18 + CRA 5 + CRACO 7 | `3000` | `frontend/` → `craco start` |
| Backend API | FastAPI + Uvicorn | `8001` (routes under `/api`) | `backend/server.py` → `app` |
| Database | MongoDB (pymongo/motor) | `27017` | `MONGO_URL` |

The frontend only *displays* backend numbers; the backend is authoritative.

---

## 2. Required environment keys

Set these in the process environment (supervisor/preview), **not** committed:

| Key | Used by | Notes |
|---|---|---|
| `MONGO_URL` | backend | e.g. `mongodb://localhost:27017` |
| `DB_NAME` | backend | e.g. `sentinel` |
| `CORS_ORIGINS` | backend | optional, defaults to `*` |
| `REACT_APP_BACKEND_URL` | frontend | e.g. `http://localhost:8001` — **required**; without it the UI calls `undefined/api` |
| `PORT` | frontend | injected by the platform; CRA/CRACO honors it |

⚠️ **Verified gotcha:** `backend/server.py` does
`load_dotenv(Path(__file__).parent / ".env")` (i.e. `backend/.env`) and then
reads `os.environ["MONGO_URL"]` / `os.environ["DB_NAME"]` **at import time**.
The repo's `.env` sits at the **repo root**, not in `backend/`, so if the
backend process has no `MONGO_URL`/`DB_NAME`, it will fail at startup with a
`KeyError`. Ensure the backend service gets those two keys from the environment.

---

## 3. Install

```bash
# Frontend (README/template target is yarn 1.22)
cd frontend && yarn install          # npm install also works

# Backend
pip install -r backend/requirements.txt
```

Notes:
- There is **no lockfile** (`yarn.lock` / `package-lock.json`) committed; the
  install resolves fresh. Consider committing one for reproducible previews.
- `scikit-learn` and `httpx` were added to `backend/requirements.txt`.
- MongoDB must be reachable; there is no bundled/embedded database.

---

## 4. Run manually in a terminal (local dev only)

⚠️ These are for a shell you drive yourself. **Do not paste them into the
preview command field** (see §5).

**Backend** (run from `backend/` so `from sentinel import ...` resolves). Keep it
running as its own process — the preview slot is only for the frontend:

```bash
cd backend
MONGO_URL=mongodb://localhost:27017 DB_NAME=sentinel uvicorn server:app --host 0.0.0.0 --port 8001
```

**Frontend dev server** (bind all interfaces; port comes from the platform):

```bash
cd frontend
HOST=0.0.0.0 REACT_APP_BACKEND_URL=http://localhost:8001 yarn start
```

---

## 5. Preview settings (Freebuff UI)

> **Each field is ONE single-line shell command.** Do not paste a multi-line
> block, comments, markdown fences, or several commands into a field. The
> runner writes the value into `cmd.sh` and executes it directly: a multi-line
> paste collapses onto one line, so the first `#` comments out the rest and a
> trailing `&&` produces `cmd.sh: syntax error: unexpected end of file`.

Fill the three fields with exactly these values:

| Field | Value (single line) |
|---|---|
| **Install** | `cd frontend && yarn install` |
| **Dev / preview command** (port `3000`) | `cd frontend && HOST=0.0.0.0 yarn start` |
| **Build** | `cd frontend && yarn build` |

CLI equivalents (if `freebuff-preview` is available):

```bash
freebuff-preview set-install "cd frontend && yarn install"
freebuff-preview set "cd frontend && HOST=0.0.0.0 yarn start" 3000
freebuff-preview set-build "cd frontend && yarn build"
```

Rules that avoid the classic failure:

- **No comments (`#`)** and **no line continuations (`\`)** in the command.
- **No `pip`/`uvicorn`/MongoDB in the preview fields.** The preview/hosting
  builder is Node-only; Python steps are rejected or break the script. The
  backend runs as a **separate managed service**.
- Need the API URL at start/build time? Keep it inline on the same line:
  `cd frontend && HOST=0.0.0.0 REACT_APP_BACKEND_URL=http://localhost:8001 yarn start`
- Prefer the repo's own scripts (`frontend/package.json`: `start`, `build`)
  over inventing new tooling.

### Production/hosting caveat
The hosting builder is Node-only and expects a static `dist/` (Vite convention).
This app is CRA (`craco build` → `build/`) **and** depends on a live API + MongoDB,
so it is a **preview target, not a pure static deploy**. Do not put `pip`/`python`
steps in the build command.

---

## 6. Readiness / health checks

| Check | Command | Expected |
|---|---|---|
| Frontend dev server | `curl -s localhost:3000/health` | `{"status":"healthy", ...}` (webpack health plugin) |
| Backend API | `curl -s localhost:8001/api/health` | engine version/integrity, `detection`, `baseline_version` |
| Backend alive | `curl -s localhost:8001/api/` | `{"message":"Hello World"}` |

The frontend dev server ships a `/health` endpoint via
`frontend/plugins/health-check/` (wired in `craco.config.js`) — use it for
readiness polling instead of guessing on a blank page.

---

## 7. Smoke test the preview

1. Open the preview URL → the SOC workspace loads and **Reset** seeds the demo.
2. Click **Next Event** until the stream pauses at the London compound anomaly
   (Rahul `rahul-006-e6`) → severity **ELEVATED** (67.98).
3. Inspect: components + availability, baseline lifecycle, Isolation Forest
   availability/fallback, ablation ladder, deterministic assistant steps.
4. Open **Evaluation & Ablation** → strict spec (70+) vs legacy detection,
   revised ablation variants, calibration sweep.

Backend-only equivalent (no browser):

```bash
cd backend
python test_v51_fixes.py
python test_phase1_persistence.py
python test_v51_boundaries.py
python test_api_routes.py
python test_sentinel_invariants.py
```

---

## 8. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Blank page, console `undefined/api/...` | `REACT_APP_BACKEND_URL` not set for the frontend process → set it and restart. |
| Backend exits immediately with `KeyError: 'MONGO_URL'` | Env keys not provided to the backend process (see §2 gotcha). |
| UI loads but every action fails / "Backend unavailable" | MongoDB down, or Mongo not reachable at `MONGO_URL`. |
| `cmd.sh: line 2: syntax error: unexpected end of file` | The preview command field holds a multi-line block/comment. Replace it with the single-line command from §5. |
| Preview never becomes ready | Check `curl localhost:3000/health`; inspect the dev-server log for webpack compile errors. |
| `reset` slow | Reset is warn-only; on a warm real MongoDB it targets < 50 ms. A slow/remote DB only warns, it does not fail. |
| Node/OpenSSL errors during start | Use Node 18/20; if `ERR_OSSL_EVP_UNSUPPORTED` appears, `NODE_OPTIONS=--openssl-legacy-provider yarn start`. |

---

## 9. What was verified

- Frontend scripts: `craco start` / `craco build` (`react-scripts` 5.0.1, `@craco/craco` 7.1.0).
- Backend entry point `server.py` → `app`, routes under `/api`, reads `MONGO_URL`/`DB_NAME` at import.
- `frontend/plugins/health-check` provides `GET /health` on the dev server.
- `freebuff-preview` / `freebuff-deploy` / `freebuff-env` are not on `PATH` in this workspace.
- No `node_modules`, no MongoDB, and no lockfiles are present in this workspace — a preview here would first need `yarn install`, the backend deps, and a reachable MongoDB.

# Farmer Assistance Platform

One-stop assistance for Indian farmers across three decisions: **PLAN** (soil, weather, crop choice), **PROTECT** (leaf checks and expert review), **SELL** (mandi prices and comparison).

> **Status: runnable MVP built on the Phase 2 contract.**
> FastAPI + SQLite backend and a React web app cover the PLAN / PROTECT / SELL journeys, expert review and an admin view. The design docs remain the source of truth for the intended production system (PostgreSQL, ONNX models, live AGMARKNET ingestion).

---

## Quickstart

Requirements: Python 3.12, Node 18+.

```bash
# 1. Backend
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows (use .venv/bin/python on Linux/macOS)
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

The backend applies Alembic migrations to `backend/farm.db` (baseline-stamping an older database), seeds reference data (9 districts, 25 crops, 18 diseases with sourced treatments, 16 mandis, 30 days of demo prices) and serves the API at `http://127.0.0.1:8000/api/v1` (`/api/docs` for OpenAPI).

```bash
# 2. Web app (second terminal)
cd web
npm install
npm run dev            # http://localhost:5173, proxies /api and /media to :8000
```

Production-style single server: `cd web && npm run build`, then restart the backend — it serves `web/dist` at `http://127.0.0.1:8000/`, including SPA deep links.

### Run on a physical device (phone / tablet on the same network)

The app is a web app, so any device on the same Wi-Fi/LAN can open it via your computer's LAN IP (e.g. `192.168.1.42`).

Find your LAN IP first:

```bash
# Windows
ipconfig
# Linux / macOS
hostname -I
```

Development mode (hot reload):

```bash
# Terminal 1 — backend, listen on all interfaces
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — web, expose Vite to the LAN
cd web
npm run dev -- --host
```

Then open `http://<YOUR_LAN_IP>:5173` on the device. The Vite proxy keeps `/api` and `/media` on the same origin, so no CORS changes are needed.

Production-style single server (simplest for a device):

```bash
cd web
npm run build
cd ../backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open `http://<YOUR_LAN_IP>:8000` on the device.

Notes:
- The device and the computer must be on the same network, and the computer's firewall must allow inbound traffic on port `5173` (dev) or `8000` (production).
- If the phone cannot connect, check that no VPN is isolating the device and that the backend is bound to `0.0.0.0` (not `127.0.0.1`).

### Production deployment

**Frontend (Vercel)**
- Project root: `web/`
- Build command: `npm run build`
- Output directory: `dist`
- Set `VITE_API_BASE` to your backend URL, e.g. `https://api.example.com/api/v1`
- SPA rewrites are configured in `web/vercel.json`

**Backend (separate host recommended: Render/Fly/Railway/VM)**
- Python service running `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Set `APP_ENV=production`, a strong `SECRET_KEY`, `ALLOW_MOCK_DATA=false`, production `DATABASE_URL` (PostgreSQL recommended), and SMS provider credentials.
- `CORS_ORIGINS` must include the Vercel frontend origin.
- Run migrations on deploy (`alembic upgrade head` or the app's startup migration).
- The SQLite file is not suitable for serverless/ephemeral hosts; use PostgreSQL in production.

### Accounts

There are no demo accounts. Create an account with phone OTP or password sign-up; the first admin must be promoted via the database or an existing admin.

Sign-in defaults to phone OTP. Password sign-in is available for accounts that set a password.

### Optional environment variables

`.env` at the repo root or `backend/.env`:

```
OPENWEATHER_API_KEY=   # live weather; otherwise a labelled deterministic demo forecast
AGMARKNET_API_KEY=     # enables admin price ingestion; otherwise demo prices only
DISEASE_CONFIDENCE_THRESHOLD=0.55
SECRET_KEY=            # required in production

# Phone OTP. "dev" sends no SMS and returns the code to the app outside production.
SMS_PROVIDER=dev       # dev | msg91 | fast2sms
SMS_API_KEY=
SMS_SENDER_ID=
SMS_TEMPLATE_ID=       # required by MSG91 (DLT-approved template)
```

In production (`APP_ENV=production`) startup refuses a default secret or `ALLOW_MOCK_DATA=true`.

## What is built

- **Auth & users** — phone-OTP signup/login with resend cooldown, expiry, attempt caps and rate limits (password login still available), rotating refresh tokens with reuse detection, logout, password change, profile, farms (max 10, primary farm).
- **PLAN** — soil report interpretation with threshold-based statuses and sourced recommendations; weather with 5-day forecast, 3-hour slots and 8 deterministic advisory rules; ranked crop recommendations with per-crop reasons and a visible suppression list.
- **PROTECT** — image upload with EXIF stripping, a green-pixel leaf gate, a demo classifier that is labelled as such, the `uncertain` path with **no treatments**, history, disease library with sourced treatments, escalation and an expert review queue that preserves the original model output.
- **SELL** — latest modal price per mandi with mandatory `arrival_date`, market comparison with distance and disclosed transport estimate, median trend series with gaps shown, rule-based selling suggestions, MSP table with source.
- **Admin/meta** — `/meta` provenance and limitations, platform stats, audit log, ingestion status.

## Honest limitations

- Mandi prices are deterministic **demo fixtures** (`source="demo_seed"`, `is_mock=true`). The API never invents a price at request time; every response carries provenance and arrival dates.
- Disease detection is a **demo heuristic keyed on the image hash**, not a trained model. It is labelled "Demo data" in the UI. Below the confidence threshold it returns `uncertain` with no treatments — a safety property, not styling.
- Crop recommendation is a **transparent rules engine**, not trained ML and not a yield prediction. `yield_range` is null by design.
- Weather uses OpenWeatherMap when a key is present; otherwise a labelled mock forecast. Advisories are always computed locally.
- OTP is implemented and durable (hashed codes, single use, 5-minute expiry, resend cooldown, hourly caps per number and IP, attempt limits), but it runs in **dev mode** until an Indian DLT-registered gateway is configured: `SMS_PROVIDER=dev` sends nothing and the API returns the code only outside production. In production without a provider, OTP requests fail with `SMS_UNAVAILABLE` instead of pretending to send. No voice or notification delivery in this build.

## Tests and checks

The API was smoke-tested end to end (auth → farm → soil → weather → recommendation → detection → escalation → expert review → prices/compare/trends → admin) and the built SPA was exercised in headless Chrome across all main routes with no console errors. There is no automated test suite yet; the task board lists it as outstanding.

## Read in this order

| Document | What it answers |
|---|---|
| [`docs/phase-1-architecture.md`](docs/phase-1-architecture.md) | What we're building, the chosen stack and why, architecture diagram, roadmap, verified external data sources |
| [`docs/02-database-design.md`](docs/02-database-design.md) | ERD, all 24 tables with columns/constraints/indexes, seed plan, migration rules |
| [`docs/02-api-spec.md`](docs/02-api-spec.md) | Every endpoint, request/response JSON, error codes, rate limits, auth matrix |
| [`docs/02-screen-flow.md`](docs/02-screen-flow.md) | Navigation map, 25 routes, per-screen states, critical journeys, accessibility + i18n rules |
| [`docs/02-decisions.md`](docs/02-decisions.md) | 11 ADRs — the decisions that are expensive to reverse |
| [`docs/02-task-board.md`](docs/02-task-board.md) | Phases 3–14 broken into tasks with exit gates |
| [`docs/02-setup-guide.md`](docs/02-setup-guide.md) | Environment setup, with exact commands |

## Principles this project holds itself to

- **No fake data in features that claim to inform.** Mocks carry `provenance.is_mock = true` and are refused in production.
- **No unvalidated accuracy claims.** Model metrics are measured and published, including the unflattering ones.
- **No silent failures.** Data freshness is visible; ingestion health is an API endpoint; "we don't know" is a designed state.
- **No LLM in the advice path.** Agronomic guidance is curated, sourced and dated — never generated.

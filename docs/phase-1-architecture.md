# Phase 1 — Requirements, Stack, Architecture, Roadmap

**Project:** One-Stop Farmer Assistance Platform (PLAN → PROTECT → SELL)
**Document status:** Phase 1 deliverable. No application code has been written yet.
**Last updated:** 2026-11-22

---

## 0. How we will work

- One phase at a time. Each phase ends with a **runnable, verifiable result** (exit criteria in §8).
- Nothing moves to the next phase until the current phase's exit criteria pass and you confirm.
- Any data that is not real is marked in code (`data_source: "mock"` in API responses) and in the UI (a visible badge). No mock data will be silently presented as real.
- External APIs are only used after verification. §10 lists what was actually verified and what was **not** available.

---

## 1. Understanding of the project

### 1.1 The problem being solved

An Indian farmer makes three high-stakes decisions every season:

1. **What and how to plant** — depends on soil, weather, season, and local climate.
2. **How to protect the crop** — disease and pest problems are usually identified late, after yield is already lost, because the nearest expert may be hours away.
3. **When and where to sell** — prices differ significantly between mandis, and the farmer often sells at the nearest mandi without knowing the spread.

These three decisions are currently served by three disconnected systems: a soil health card on paper, word-of-mouth weather advice, and a phone call to a broker. The platform's value is **one app, one profile, three connected modules**, where data flows between them (e.g. your crop choice determines which diseases we warn you about; your district determines which mandis we compare).

### 1.2 Users and roles

| Role | Who | What they need |
|---|---|---|
| `farmer` | Small/marginal farmer, possibly low literacy, often a shared phone | Large buttons, voice, local language, no jargon |
| `expert` (Krishi Mitra) | CSC operator / agri graduate / extension officer | Queue of farmer-submitted images, ability to confirm or correct an AI result, respond to consultations |
| `admin` | Project operator | Manage crops, markets, scheme content, view usage stats, moderate |

### 1.3 Functional scope

**PLAN**
- Soil health: manual entry of N/P/K, pH, organic carbon, EC; optional Soil Health Card PDF (later phase, OCR); interpretation against crop-specific thresholds; plain-language recommendations.
- Weather: current conditions + multi-day forecast for the farmer's location; derived farm advisories (spray window, irrigation advice, frost/heat/heavy-rain warnings).
- Crop recommendation: ranked crop suggestions with a per-crop "why", expected season, and estimated yield range **only where a validated model exists**.

**PROTECT**
- Leaf image capture/upload → disease prediction with top-3 candidates + confidence, symptoms, severity, treatment steps, and an explicit "not a diagnosis — verify with an expert" limitation.
- Pest information library (curated reference content, not AI-generated).
- Weather-linked disease risk alerts (e.g. high humidity + temperature band → blight risk for the selected crop).
- History of past detections with images.
- Expert review path: escalation of a detection to an `expert` for confirmation.

**SELL**
- Daily mandi prices from the official AGMARKNET feed, filtered by state/district/commodity.
- Compare the same commodity across nearby mandis; show modal/min/max and the arrival date.
- Price trend chart from accumulated daily snapshots (our own history table — the upstream API is a daily snapshot, not a time series).
- Market suggestions ranked by price net of an estimated transport cost (distance × rate), clearly labelled as an estimate.
- MSP / procurement info as **curated reference data** with a source link and "last verified" date (no official live procurement API exists — see §10).

**Cross-cutting (later phases)**
- Dashboard, multilingual UI (en + hi first, then regional), voice assistant, SMS/IVR architecture, role-based admin.

### 1.4 Explicit non-goals for the MVP

- No e-commerce/checkout, no payments, no logistics booking. SELL is decision support, not a marketplace transaction engine.
- No live mandi ticker. AGMARKNET is daily administrative data with publication delays; we will label it as such.
- No microservices. One backend process + one worker process + one database in Docker Compose.
- No on-device model training, no drone/satellite imagery, no IoT sensor integration.
- No claim of "diagnosis". Every AI output is phrased as a *possible* match with confidence and limitations.

---

## 2. MVP definition (what "done" means for v1)

**MVP = a farmer can, on a real phone, in Hindi or English:**
1. register/login with a phone number,
2. save a farm location and soil values,
3. see weather + a weather advisory for that location,
4. get a ranked crop recommendation with reasons,
5. photograph a leaf and get a disease prediction with treatment guidance and a disclaimer,
6. see today's mandi prices for their district and compare 3 nearby mandis,
7. see all of the above on one dashboard,
8. (admin) see users, detections, and correct a detection.

**MVP is explicitly *not* blocked on:** SMS/IVR, voice assistant, PDF soil-card OCR, yield prediction model, regional languages beyond Hindi, expert live chat.

Dependency order is important: **voice, SMS, and regional languages are additive layers over working screens**, so they come after the three modules function. That keeps the first demo date realistic.

---

## 3. Technology stack (decided)

Verified against the current machine: Docker 29.7.2, Node 24.18.0, npm 12.0.2, Git 2.55.0, **Python 3.14.7**.

> ⚠️ Python 3.14 is too new for the ML stack. PyTorch and several scientific wheels lag new CPython releases, and a training environment that cannot install `torch` is a dead end. **Pin Python 3.12** everywhere (Docker base image + local venv). This is the single most common setup failure in projects like this.

| Layer | Choice | Why this one |
|---|---|---|
| Mobile app | **React Native + Expo (TypeScript)**, Expo Router, React Query | One codebase for Android/iOS; Expo gives camera (`expo-image-picker`), speech, and OTA updates without native tooling; camera access is essential for PROTECT. |
| Web admin | **React + TypeScript + Vite**, TanStack Query, shadcn/ui + Tailwind | Admin is a small internal tool. Vite keeps it light and fast to build; no SSR need. |
| Backend | **Python 3.12 + FastAPI + Pydantic v2** | Same language as the ML code (no second runtime, no model-serving bridge). Async I/O suits many small external API calls. Pydantic gives request validation and OpenAPI docs for free — the mobile team gets typed clients. |
| ORM / migrations | **SQLAlchemy 2.0 (async) + asyncpg + Alembic** | Mature, typed, and Alembic is the standard migration path for Postgres. |
| Database | **PostgreSQL 16** | Relational fits this domain (users → farms → detections → prices). PostGIS not needed for MVP; plain lat/lon + Haversine is enough for "nearby mandis". |
| Cache / queue | **Redis 7** — introduced in Phase 11 only | Needed for rate limiting, weather/mandi response caching, and a job queue for alert fan-out. Not part of the MVP spine; adding it early is unnecessary complexity. |
| Image storage | **Cloudflare R2** (S3-compatible; 10 GB-month free, zero egress) behind a `StorageProvider` interface, with a **local-disk driver for development** | Lets us build and test without cloud credentials; R2 avoids S3's egress charges, which matter for an image-heavy app. |
| Disease model | **PyTorch + `timm`**, transfer learning on MobileNetV3 / EfficientNet-B0, exported to ONNX for cheap CPU inference | Small models run on a CPU container; ONNX keeps the serving image light and portable. |
| Crop recommendation | **scikit-learn** (GradientBoosting/RandomForest) + a **deterministic agronomic rule layer** | Tabular problem with ~7 features — a tree ensemble is the right size; the rule layer supplies season/agro-zone logic the dataset lacks. |
| Weather | **OpenWeatherMap** free tier (current + 5-day/3-hour forecast) with **Open-Meteo** as a no-key fallback | Verified free limits in §10. |
| Mandi prices | **data.gov.in AGMARKNET resource** (official, free tier with API key), nightly snapshot job | Official government source; the only one with national coverage. |
| Voice / language | **Bhashini (ULCA/Dhruva)** for ASR/TTS/NMT; `expo-speech` as offline TTS fallback in dev | National Indian-language stack, free to start, covers 22+ languages in one API. |
| SMS | Provider-agnostic `NotificationChannel` abstraction; first real driver = MSG91 or Fast2SMS, **blocked on DLT registration** | TRAI mandates DLT entity/header/template registration for any SMS to Indian numbers. This is paperwork, not code, and it must be planned for early (see §10). |
| Auth | **JWT** (short-lived access + rotating refresh), **Argon2id** password hashing, role-scoped dependencies | Standard, stateless, works with the mobile client's secure storage. |
| Containerisation | **Docker + Docker Compose**; multi-stage builds, non-root user | One command brings up db + api + admin. |
| CI | **GitHub Actions**: lint, typecheck, pytest, Alembic check, image build | Catches the failures that actually hurt (migration drift, type errors). |

### Rejected, with reasons

- **Node/NestJS backend** — would mean two languages and a separate Python model service; more moving parts, no benefit.
- **TensorFlow** — fine technically, but PyTorch + timm has better pretrained-model ergonomics for this specific task; mixing both is gratuitous.
- **MongoDB** — this data is highly relational (users, farms, detections, markets). Postgres also gives us price history aggregation in SQL.
- **Next.js for admin** — SSR buys nothing for an internal dashboard and adds a server to deploy. Vite + static build serves from nginx.
- **Microservices** — explicitly out of scope per your rules; modules stay separate *in code*, deployed together.
- **Firebase/Supabase as the whole backend** — would hide the architecture you're trying to learn and lock the ML layer out.

---

## 4. System architecture

### 4.1 Container view

```
                        ┌──────────────────────────┐
                        │  Farmer (Android/iOS)    │
                        │  Expo RN app (TS)        │
                        └────────────┬─────────────┘
                                     │ HTTPS / JSON  (JWT Bearer)
                        ┌────────────▼─────────────┐
                        │  Admin / Expert          │
                        │  React + Vite (SPA)      │
                        └────────────┬─────────────┘
                                     │
                        ┌────────────▼─────────────┐
                        │  nginx (TLS, static,     │
                        │  reverse proxy /api)     │
                        └────────────┬─────────────┘
                                     │
     ┌───────────────────────────────▼───────────────────────────────┐
     │                    FastAPI application  (app/)                │
     │                                                               │
     │  middleware: request-id · CORS · rate limit · error handler    │
     │                                                               │
     │  ┌─────────── modules (HTTP layer + service layer) ─────────┐  │
     │  │ auth │ users │ soil │ weather │ crops │ disease │         │  │
     │  │ markets │ notifications │ voice │ admin                  │  │
     │  └───────┬───────────────────────────────────┬───────────── ┘  │
     │          │                                   │                │
     │  ┌───────▼──────────┐               ┌────────▼─────────────┐   │
     │  │ integrations/    │               │ ml/ (inference)      │   │
     │  │ openweather      │               │ disease  (ONNX)      │   │
     │  │ agmarknet        │               │ crop_rec (joblib)    │   │
     │  │ bhashini         │               │ rule engine          │   │
     │  │ sms · storage    │               └────────┬─────────────┘   │
     │  └───────┬──────────┘                        │                │
     └──────────┼───────────────────────────────────┼────────────────┘
                │                                   │
     ┌──────────▼─────────┐  ┌──────────────┐  ┌────▼──────────────┐
     │ worker (arq/APSched)│ │ PostgreSQL 16│  │ model artifacts   │
     │ nightly price pull  │ │  + Alembic   │  │ (./ml_artifacts)  │
     │ alert fan-out       │ └──────────────┘  └───────────────────┘
     └──────────┬──────────┘  ┌──────────────┐  ┌───────────────────┐
                │             │ Redis (P11)  │  │ R2 / local disk   │
                │             └──────────────┘  │ crop images       │
                ▼                                └───────────────────┘
     ┌────────────────────┐
     │ External services  │
     │ OpenWeatherMap     │
     │ data.gov.in        │
     │ Bhashini           │
     │ SMS provider       │
     └────────────────────┘
```

### 4.2 Why this shape

- **One deployable backend, modules inside.** Each module owns `router.py` (HTTP), `schemas.py` (validation), `service.py` (business logic), `models.py` (DB). Modules talk to each other **through service functions, not by importing each other's routers**. This gives clean boundaries without the operational cost of microservices.
- **`integrations/` is the only place that knows a vendor's wire format.** If we swap OpenWeatherMap for Open-Meteo, or MSG91 for Fast2SMS, nothing above that layer changes. Each integration has a timeout, retry with backoff, and a typed error.
- **`ml/` exposes a stable `predict_*` contract.** The API never knows whether inference is ONNX, PyTorch, or a canned baseline. This lets the API work on day one with a clearly-labelled baseline model and swap in the trained model without touching endpoints.
- **Worker is separate** so slow jobs (thousands of mandi rows, alert fan-out) never block request latency.
- **Storage is behind `StorageProvider`** so development runs on local disk and production on R2, using the same call sites.

### 4.3 Request flow examples

**Disease detection (the most complex path)**
```
mobile: pick image → client-side resize/compress (≤1600px, JPEG) → POST /api/v1/disease/detect (multipart)
  → auth dependency (jwt → user)
  → validate: mime by magic bytes, size ≤ 8 MB, dimensions ≥ 224px, reject non-images
  → store image (R2/local) → create crop_images row
  → preprocess: decode with OpenCV, centre-crop, resize 224, normalise
  → model.predict → logits → softmax → top-3 (label, confidence)
  → confidence gate: max(conf) < threshold → status="uncertain", advise expert review
  → enrich: disease metadata (symptoms, treatment, severity) from reference table
  → create disease_detections row (model_version, latency, confidence, image_id)
  → respond with prediction + limitations text + expert-escalation option
```

**Mandi prices**
```
nightly worker → agmarknet client (paged, rate-limited, retries)
  → normalise rows (state/district/market/commodity/variety/grade/date/3 prices)
  → upsert into mandi_prices (unique key on market+commodity+variety+grade+date)
  → record ingestion run + row counts (observability)

request → GET /api/v1/markets/prices?commodity=onion&district=Pune
  → read from our DB (never call upstream inside a request path)
  → response includes arrival_date + retrieved_at + data_source
```

**Crop recommendation**
```
POST /api/v1/crops/recommend { farm_id, soil{...}, season }
  → fill climate features from latest weather cache (temperature, humidity, rainfall)
  → ML model → probability per crop
  → rule layer: filter by season and agro-climatic zone; penalise crops not
    recommended for the zone; attach reason strings
  → rank → return top-N with per-crop reasons + dataset provenance + confidence band
```

**Weather advisory**
```
GET /api/v1/weather/forecast?farm_id=...
  → cache check (Redis in P11 / TTL table before that)
  → OpenWeatherMap forecast → normalise
  → advisory rules (deterministic, testable): rain > X in 24h → "delay spraying";
    temp_min < 4°C → frost warning; humidity>85 & temp 20–30 → fungal risk
  → response: forecast + advisories[] each with rule_id and severity
```
Note: the free weather tier has no government weather alerts, so advisories are **our own deterministic rules over forecast data** — and we say so in the UI.

### 4.4 Model integration flow (training → serving)

```
ml/disease/train.py  (dev/Colab GPU, NOT in production image)
   dataset → augmentation → transfer learning → val metrics
   → evaluate on held-out + a small field-photo set
   → export ONNX + write model_card.json (version, accuracy, per-class metrics, date, dataset hash)
   → artifact committed to ml_artifacts/ (gitignored) or pulled into the image at build

runtime: ml/registry.py loads artifact once at startup, checks version against
an expected checksum, exposes predict(); /healthz reports model_version
```
Every detection row stores `model_version`, so old results remain explainable after a retrain. Retraining never silently changes historical responses.

---

## 5. Proposed folder structure (monorepo)

```
farm/
├─ README.md                     # quickstart: one command to run everything
├─ docker-compose.yml            # db + api + worker + admin (dev & prod profiles)
├─ docker-compose.override.yml   # dev-only: bind mounts, hot reload, exposed ports
├─ .env.example                  # every var documented; real .env is gitignored
├─ .gitignore  .editorconfig  .pre-commit-config.yaml
├─ docs/
│  ├─ phase-1-architecture.md    # this file
│  ├─ api.md                     # generated from OpenAPI + hand-written notes
│  ├─ decisions/                 # ADRs: why Postgres, why ONNX, etc.
│  └─ data-sources.md            # provenance, licensing, last-verified dates
│
├─ backend/
│  ├─ Dockerfile                 # multi-stage, python:3.12-slim, non-root
│  ├─ pyproject.toml             # deps + ruff + mypy + pytest config
│  ├─ alembic.ini
│  ├─ alembic/versions/          # one migration per schema change
│  ├─ app/
│  │  ├─ main.py                 # app factory, router mounting, middleware, lifespan
│  │  ├─ core/
│  │  │  ├─ config.py            # pydantic-settings, fails fast on missing secrets
│  │  │  ├─ db.py                # async engine, session factory
│  │  │  ├─ security.py          # argon2, JWT encode/decode
│  │  │  ├─ deps.py              # get_db, current_user, require_role(...)
│  │  │  ├─ errors.py            # AppError hierarchy → JSON error contract
│  │  │  ├─ logging.py           # structured logs w/ request-id
│  │  │  └─ pagination.py
│  │  ├─ modules/
│  │  │  ├─ auth/                # register, login, refresh, logout
│  │  │  ├─ users/               # profile, farms, role management
│  │  │  ├─ soil/                # analyze, history
│  │  │  ├─ weather/             # current, forecast, advisories
│  │  │  ├─ crops/               # recommend, catalog, history
│  │  │  ├─ disease/             # detect, history, escalate, expert review
│  │  │  ├─ markets/             # markets, prices, compare, trends
│  │  │  ├─ notifications/       # in-app + sms channels (P11)
│  │  │  ├─ voice/               # query → intent → answer (P10)
│  │  │  └─ admin/               # stats, moderation, reference data CRUD
│  │  ├─ integrations/
│  │  │  ├─ base.py              # HttpClient: timeout, retry, error mapping
│  │  │  ├─ weather_openweather.py  weather_openmeteo.py
│  │  │  ├─ agmarknet.py
│  │  │  ├─ bhashini.py
│  │  │  ├─ sms/  (base.py, msg91.py, console.py)
│  │  │  └─ storage/ (base.py, local.py, r2.py)
│  │  ├─ ml/
│  │  │  ├─ registry.py
│  │  │  ├─ disease/ (preprocess.py, predictor.py, labels.py)
│  │  │  ├─ crop_rec/ (predictor.py, rules.py)
│  │  │  └─ reference/           # disease metadata, crop calendar, treatment text (JSON/CSV)
│  │  ├─ db/
│  │  │  ├─ base.py              # DeclarativeBase, naming conventions
│  │  │  ├─ models/              # SQLAlchemy models, one file per aggregate
│  │  │  └─ seed/                # crops, markets, diseases, advisories (versioned data)
│  │  └─ jobs/                   # worker entrypoints: ingest_prices, send_alerts
│  ├─ ml_artifacts/              # *.onnx, *.joblib, model_card.json  (gitignored)
│  └─ tests/
│     ├─ unit/                   # services, rules, security
│     ├─ api/                    # endpoint contracts (httpx AsyncClient)
│     └─ integration/            # db + storage, mocked externals via respx
│
├─ ml/                           # training only; never deployed
│  ├─ disease/ (data/ .gitignored, train.py, evaluate.py, export_onnx.py, model_card.py)
│  ├─ crop_recommendation/ (data/, train.py, evaluate.py, rules_eval.py)
│  └─ notebooks/
│
├─ mobile/
│  ├─ app.json  eas.json  tsconfig.json  package.json
│  ├─ app/                       # expo-router routes = screens
│  │  ├─ (auth)/ login.tsx register.tsx onboarding.tsx
│  │  ├─ (tabs)/ index.tsx plan.tsx protect.tsx sell.tsx profile.tsx
│  │  ├─ plan/ soil.tsx weather.tsx recommendation.tsx
│  │  ├─ protect/ capture.tsx result/[id].tsx history.tsx
│  │  └─ sell/ prices.tsx compare.tsx trend.tsx
│  ├─ src/
│  │  ├─ api/ (client.ts, auth.ts, soil.ts, weather.ts, crops.ts, disease.ts, markets.ts)
│  │  ├─ components/ (Button, Card, BigAction, ConfidenceBar, Disclaimer, LangSwitch)
│  │  ├─ theme/ (colors, spacing, typography — large-text-first scale)
│  │  ├─ i18n/ (en.json, hi.json, index.ts)
│  │  ├─ hooks/  store/ (auth token in expo-secure-store)
│  │  └─ lib/ (image.ts compress helper, format.ts)
│  └─ assets/
│
├─ admin-web/
│  ├─ vite.config.ts  tsconfig.json  index.html
│  └─ src/ (main.tsx, router.tsx, api/, pages/, components/, lib/)
│
└─ infra/
   ├─ nginx/default.conf
   ├─ scripts/ (dev_up.sh, db_reset.sh, seed.sh)
   └─ .github/workflows/ci.yml
```

**Why these boundaries:** `app/modules/*` maps 1:1 to the API prefixes you specified, so `/api/v1/soil/*` lives in exactly one place. `integrations/` and `ml/` are the only vendor/model-aware folders, which is what makes swapping providers cheap. `ml/` (training) is deliberately separate from `app/ml` (inference) so the production image never carries datasets or training deps.

---

## 6. API surface (planned, versioned under `/api/v1`)

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/otp/request`, `POST /auth/otp/verify` |
| Users | `GET/PATCH /users/me`, `GET/POST /users/me/farms`, `PATCH/DELETE /users/me/farms/{id}`, `GET /users` (admin), `PATCH /users/{id}/role` (admin) |
| Soil | `POST /soil/analyze`, `GET /soil/reports`, `GET /soil/reports/{id}` |
| Weather | `GET /weather/current?farm_id=`, `GET /weather/forecast?farm_id=&days=`, `GET /weather/advisories?farm_id=` |
| Crops | `GET /crops` , `POST /crops/recommend`, `GET /crops/recommendations`, `GET /crops/recommendations/{id}` |
| Disease | `POST /disease/detect`, `GET /disease/detections`, `GET /disease/detections/{id}`, `POST /disease/detections/{id}/escalate`, `PATCH /disease/detections/{id}/review` (expert), `GET /disease/library`, `GET /disease/risk-alerts?farm_id=` |
| Markets | `GET /markets`, `GET /markets/prices`, `GET /markets/compare`, `GET /markets/trends`, `GET /markets/suggestions?farm_id=`, `GET /markets/msp` |
| Voice | `POST /voice/query` (audio or text → intent → answer + optional TTS) |
| Notifications | `GET /notifications`, `PATCH /notifications/{id}/read`, `POST /notifications/subscribe` |
| Admin | `GET /admin/stats`, `GET/POST/PATCH` reference data (diseases, crops, advisories, MSP), ingestion status |

Conventions from day one: envelope `{ data, meta }` for lists (page/limit/total), error contract `{ error: { code, message, details, request_id } }`, ISO-8601 UTC timestamps, `X-Request-ID` on every response. Full request/response schemas are produced as OpenAPI at `/api/docs`, plus a hand-written `docs/api.md` per phase.

---

## 7. Security baseline (implemented from Phase 5, not retrofitted)

- Argon2id password hashing; no plaintext or reversible storage; login rate-limited per IP **and** per account.
- JWT: 15-min access token, 7-day refresh with rotation + revocation list; refresh token in `expo-secure-store`, never `AsyncStorage`.
- Role checks as a dependency (`require_role("expert")`), enforced server-side only.
- Uploads: validate magic bytes (not the `Content-Type` header), enforce size/dimension limits, re-encode through Pillow/OpenCV to strip EXIF and payloads, store with random UUID names, serve via signed URLs — never execute or inline-serve user files.
- All secrets via env; `.env` gitignored; `config.py` refuses to boot in production with a weak/default `SECRET_KEY`.
- Parameterised SQL only (ORM); Postgres not exposed publicly in production compose.
- Structured error logging with request IDs; no stack traces or internal paths in API responses; no PII in logs (phone numbers masked).
- Per-endpoint rate limits, tighter on `/auth/*` and `/disease/detect` (compute cost).

---

## 8. Development roadmap with exit criteria

| Phase | Deliverable | Exit criteria (verifiable) |
|---|---|---|
| **1. Requirements & stack** | This document | You approve stack + scope + folder structure |
| **2. Architecture & planning** | DB ERD, API spec, screen-flow map, ADRs, task board | ERD reviewed; every screen mapped to endpoints |
| **3. Environment & Docker** | Composed dev stack | `docker compose up` → api `/healthz` OK, db reachable, admin loads, hot reload works |
| **4. Database** | Models + Alembic migration + seed data | `alembic upgrade head` clean on empty DB; `alembic downgrade base` clean; seed idempotent; relationships tested |
| **5. Backend & auth** | Auth, users, farms, RBAC, error contract | pytest auth suite passes; register→login→refresh→me works via curl; 401/403 covered |
| **6. Mobile app** | Expo scaffold, auth flow, dashboard shell, i18n skeleton | Real device (Expo Go) logs in, persists session, shows dashboard with farm context |
| **7. PLAN module** | Soil, weather, crop recommendation end-to-end | Real weather for a real district; recommendation with reasons; soil report saved + retrieved |
| **8. PROTECT module** | Model trained + ONNX serving + capture/result/history + expert escalation | Held-out metrics + model card recorded; field-photo sanity check reported honestly; end-to-end on device |
| **9. SELL module** | AGMARKNET ingestion + prices/compare/trends + suggestions | Nightly job ingests real rows; compare returns like-with-like variety/grade; trends from accumulated snapshots |
| **10. Voice & multilingual** | Bhashini ASR/TTS/NMT, hi+en UI complete | Hindi voice query returns spoken Hindi answer for weather/price intent |
| **11. Admin & notifications** | Admin dashboard, in-app alerts, SMS channel (DLT pending) | Admin can correct a detection; alert rules fire from forecast; SMS driver sends to a test number once DLT is approved |
| **12. Testing & hardening** | Coverage targets, load test, security pass | CI green; documented coverage; rate limits verified; no high-severity findings |
| **13. Deployment** | Prod compose/VPS, TLS, backups, monitoring | Public HTTPS URL; automated daily DB backup + restore rehearsal |
| **14. Docs & demo** | README, API docs, model cards, demo script | A new developer can run the stack from README alone |

Phase 2 is documentation-only; Phases 3–5 produce the first runnable demo (API + DB + admin), Phase 6 adds the phone. **First full PLAN→PROTECT→SELL demo at the end of Phase 9.**

---

## 9. Environment checklist (this machine)

Already present: Docker 29.7.2 ✅, Node 24.18.0 ✅, npm 12.0.2 ✅, Git 2.55.0 ✅, Python 3.14.7 ⚠️ (too new for ML — install 3.12).

```bash
# 1. Python 3.12 (side-by-side with 3.14)
winget install -e --id Python.Python.3.12
py -0p                     # confirm 3.12 is listed

# 2. Verify Docker engine is actually running (Docker Desktop must be started)
docker info --format '{{.ServerVersion}}'

# 3. (Phase 4+) Postgres client, optional — the DB runs in Docker
winget install -e --id PostgreSQL.PostgreSQL.16    # optional; skip if you prefer psql inside the container

# 4. Expo tooling (Phase 6)
npm i -g expo-cli eas-cli   # or use npx expo, no global install needed

# 5. Expo Go app on your Android phone (from Play Store) — required for device testing

# 6. Git identity (if not already set)
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Accounts/keys to obtain (start early — approval latency is real, not code):
1. **data.gov.in API key** — register → profile → API key. Instant.
2. **OpenWeatherMap API key** — free plan. New keys can take up to ~2h to activate.
3. **Bhashini** — register on the ULCA dashboard; approval typically 1–2 business days (needed at Phase 10, register now).
4. **Cloudflare R2** — bucket + S3 API token (needed at Phase 8; local disk works until then).
5. **SMS provider + DLT** — entity registration, header, content templates. Slowest item; begin at Phase 1 if SMS matters for your demo.

---

## 10. External data sources — verified 2026-11-22

| Need | Source | Status / cost | Verified facts | Risks / fallback |
|---|---|---|---|---|
| Mandi prices | **data.gov.in** resource `9ef84268-d588-465a-a308-a864a43d0070` ("Current Daily Price of Various Commodities from Various Markets"), Ministry of Agriculture & Farmers Welfare | Free, API key required, GODL-India licence | Endpoint `api.data.gov.in/resource/{id}?api-key=…&format=json`; fields state, district, market, commodity, variety, grade, arrival_date, min/max/modal price; supports `filters`, `offset`, `limit`; ~1,000 rows/page; ~13k rows/day nationally | **Daily snapshot, not live.** Publication lag/missing mandis are normal. We cache in our DB and always display `arrival_date`. Alt: CEDA Agmarknet API (api.ceda.ashoka.edu.in) for historical depth |
| Weather | **OpenWeatherMap** free plan | Free: 60 calls/min, 1,000,000 calls/month (Current Weather, 5-day/3-hour forecast, geocoding) | Free tier does **not** include government alerts (that's One Call, a separate subscription with 1,000 calls/day) → we derive advisories ourselves | Cache per location; Alt: **Open-Meteo** (no key, generous free limits, CC-BY) as the drop-in fallback |
| Disease images (training) | **PlantVillage** (Mohanty et al. 2016) | Free, CC-BY-SA 3.0 / CC0 variants | 54,306 images, 14 crops, 26 diseases; `datasets.load_dataset("mohanty/PlantVillage")`; leaf-grouped 80/20 split to prevent leakage | **Lab-condition images** (single leaf, plain background). Field accuracy will be materially lower — see §11 |
| Crop recommendation (training) | Kaggle "Crop Recommendation Dataset" (atharvaingle) | Free, ~2,200 rows, 22 crops | Features N,P,K,temperature,humidity,pH,rainfall; **built by augmenting rainfall/climate/fertiliser datasets** → effectively synthetic; published "99% accuracy" is on this synthetic distribution | Not a validated agronomic model. Treat as a prior; add rule layer + agro-climatic zone data; never advertise accuracy figures |
| Soil health | **Soil Health Card scheme** | No public per-farm API found | Portal provides scheme info/reports, not a queryable farm-level API | Farmer enters values manually; PDF/OCR import later; interpretation rules from ICAR/state package-of-practices, curated into `ml/reference/` |
| Crop/agronomy reference | ICAR / state agriculture department **Package of Practices**, crop calendars | Free, public documents | Not machine-readable | Hand-curated JSON/CSV, each row with `source_url` + `last_verified`; admin-editable |
| MSP / procurement | CACP / Department of Food & Public Distribution published MSP tables | Free, published as tables/PDFs, **no live API** | — | Curated table per season with source link + effective date; UI shows "as published on <date>", never implied live |
| Voice / ASR / TTS / translation | **Bhashini** (ULCA / Dhruva) | Free to start, registration + DIBD approval (1–2 business days) | REST: `dhruva-api.bhashini.gov.in/services/inference/pipeline`; pipeline config via `meity-auth.ulcacontrib.org`; ASR service IDs per language (e.g. `ai4bharat/conformer-hi-gpu--t4`); TTS + NMT pipelines; ASR needs 16 kHz mono WAV/MP3 base64 | Approval latency + per-call latency; fallback: `expo-speech` (device TTS) and on-device/OS speech recognition for dev, English-only |
| SMS | Provider (MSG91 / Fast2SMS / Exotel; or aggregator Sent) | Paid per SMS; **DLT registration mandatory** | TRAI requires Principal Entity registration, approved Header (6-char alphanumeric for transactional), approved Content Template; template ID passed with each send; DND hours 21:00–10:00 restrictions | Paperwork takes days–weeks; build channel abstraction now, keep SMS behind a feature flag |
| Object storage | **Cloudflare R2** | Free: 10 GB-month, 1M Class A, 10M Class B ops, **zero egress fees**; then $0.015/GB-month | S3-compatible API; partial S3 feature coverage | Dev uses local disk; R2 from Phase 8. Alt: Backblaze B2 |
| Yield estimation | data.gov.in crop production statistics / ICRISAT district yields | Free datasets, no model | Requires district-level yield + weather + management data and careful validation | **Deferred.** If built, output is a *range with stated error*, labelled "estimate", never a promise |

**Rule applied throughout:** if a source is unavailable, degraded, or unapproved at build time, the feature either (a) uses a clearly-labelled mock driver in dev, or (b) is disabled with an explicit "unavailable" state. Never a silent fake.

---

## 11. AI/ML plan and honesty policy

### Disease detection
- **Approach:** transfer learning (MobileNetV3-Large or EfficientNet-B0, ImageNet weights) on PlantVillage with strong augmentation (rotation, crop, brightness/contrast, blur, JPEG artifacts, background substitution) to narrow the lab→field gap. Export to ONNX for CPU inference.
- **Serving:** loaded once at startup, `model_version` recorded per detection. Target p95 < 1.5 s on CPU for a 224px image.
- **Evaluation:** leaf-grouped held-out split (no leakage), per-class precision/recall/F1, confusion matrix, **calibration** (are 90% confidence predictions right 90% of the time?), plus a separate small set of real field photos.
- **Product consequences of limited validation** (not optional):
  - show top-3 with confidences, not one definitive answer;
  - `confidence < threshold` → "uncertain, request expert review" instead of a guess;
  - reject non-leaf/blank images via a leaf-detector gate;
  - persistent disclaimer: *"AI estimate, not a diagnosis. Confirm with your Krishi Mitra before spending on chemicals."*
  - every result offers **escalate to expert**.
- **Known limitation stated in the report:** PlantVillage is photographed under controlled conditions; reported lab accuracies do not transfer to field photos. We will publish our own measured field-set accuracy even if it's unflattering.

### Crop recommendation
- **Approach:** GradientBoosting/RandomForest on the 7 features + a deterministic rule layer (season, agro-climatic zone, crop rotation, water availability) that can veto or boost candidates.
- **Honesty:** the public dataset is augmented/synthetic; ~99% accuracy figures circulating online measure fit to that synthetic distribution, not agronomic validity. We will therefore (1) report honest cross-validated metrics, (2) show per-crop probability bands, (3) explain every recommendation with the contributing factors, (4) label the outcome as a suggestion, (5) never show a single "best crop" without alternatives.
- **Yield estimate:** only after a validated model exists. Until then the UI shows "expected yield data not available for this crop/district" rather than a fabricated number.

### Reference content (not AI)
Symptoms, treatment guidance, pest info, MSP, and scheme details are **curated reference data with sources and verification dates**, seeded into the DB and editable by admins. An LLM will not generate pesticide dosage advice — the liability and hallucination risk are unacceptable for advice that affects health and crops.

---

## 12. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Python 3.14 breaks ML installs | Blocks Phase 8 | Pin 3.12 in Docker + venv; CI uses 3.12 |
| PlantVillage → field accuracy drop | Farmer trust, safety | Field-set evaluation, confidence gate, top-3, expert escalation, explicit disclaimer |
| AGMARKNET API lag / missing districts | Empty SELL screens | Cache + `arrival_date` display + empty-state copy; district→nearest-mandi fallback |
| DLT registration delay | No SMS in demo | Start paperwork early; SMS behind a flag; in-app notifications carry MVP |
| Bhashini approval/latency | Voice demo slips | Device TTS fallback; voice is Phase 10, after core value works |
| Weather API key quota exhaustion | Advisories fail | Per-location caching, single fetch reused across users, Open-Meteo fallback |
| Ranching form fields for low-literacy users | Low adoption | Voice input where possible, big presets ("my soil test says..."), sane defaults, minimal required fields |
| Scope creep (marketplace, chat, yield) | Never ships | MVP list in §2 is the contract; new ideas go to a backlog file |

---

## 13. Decisions I need from you before Phase 2

1. **Primary state/region** — drives mandi seeding, crop catalog, language set, and agro-climatic zones. (Default if you don't care: Maharashtra + a second state, using national AGMARKNET data.)
2. **Do you have a GPU or Colab access?** Training the disease model on CPU is possible but slow; Colab/Kaggle free GPU changes the Phase 8 plan.
3. **Is a second login method needed at MVP?** I propose phone + password, with OTP as a later addition (OTP needs SMS/DLT, which is slow).
4. **Does the demo need to run on a physical phone**, or is an Android emulator acceptable? This affects Phase 3/6 setup depth.
5. **Web admin scope** — full dashboard at Phase 11, or a minimal "review detections" screen earlier?

---

## 14. Development checklist

- [x] Phase 1 — requirements understood, stack decided, data sources verified, architecture drafted
- [ ] Phase 2 — ERD, API spec, screen flow, ADRs
- [ ] Phase 3 — Docker dev environment running
- [ ] Phase 4 — PostgreSQL schema + migrations + seed
- [ ] Phase 5 — Auth + users + farms + RBAC
- [ ] Phase 6 — Mobile app shell + auth
- [ ] Phase 7 — PLAN module
- [ ] Phase 8 — PROTECT module + model
- [ ] Phase 9 — SELL module + AGMARKNET
- [ ] Phase 10 — Voice + multilingual
- [ ] Phase 11 — Admin + notifications
- [ ] Phase 12 — Testing & hardening
- [ ] Phase 13 — Deployment
- [ ] Phase 14 — Documentation & demo

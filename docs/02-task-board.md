# Phase 2 — Task Board (Phases 3–14)

Sizes: **S** < half a day · **M** 1–2 days · **L** 3–5 days. Each phase has a hard exit gate; a phase is not "done" until every box is ticked and the gate passes.

Rule: **no phase starts before the previous gate passes**, except documentation tasks in Phase 2/14 which may run in parallel.

---

## Phase 3 — Environment & Docker

**Goal:** one command brings up the full dev stack, with hot reload.

- [ ] **S** `backend/Dockerfile` — multi-stage, `python:3.12-slim`, non-root user, `uvicorn --reload` in dev
- [ ] **S** `backend/pyproject.toml` — deps pinned, ruff + mypy + pytest configured
- [ ] **M** `docker-compose.yml` — `db` (postgres:16, named volume, healthcheck), `api`, `worker`
- [ ] **S** `docker-compose.override.yml` — bind mounts, ports 8000/5432, dev env
- [ ] **S** `.env.example` — every variable documented with a safe default
- [ ] **S** `app/main.py` — factory, lifespan, `/healthz`, `/readyz`, `/meta`, CORS
- [ ] **S** `app/core/config.py` — pydantic-settings, fail-fast on missing/weak secrets
- [ ] **S** `app/core/logging.py` — JSON logs with request id
- [ ] **S** `.github/workflows/ci.yml` — ruff, mypy, pytest (no DB yet)
- [ ] **S** `infra/scripts/dev_up.sh` — build, up, wait for health, print URLs

**Gate:** `docker compose up --build` from a clean clone → `GET /healthz` returns 200, `/readyz` reports db ok, logs are structured, CI green. Verify: bring it down with `-v` and up again.

---

## Phase 4 — Database

**Goal:** the schema in `02-database-design.md` exists, migrates both ways, and is seeded.

- [ ] **M** `db/base.py` — DeclarativeBase, naming convention, `created_at`/`updated_at` mixin
- [ ] **M** All 24 models, split by aggregate (`users.py`, `farms.py`, `plan.py`, `protect.py`, `sell.py`, `reference.py`, `ops.py`)
- [ ] **M** Enums as Python `StrEnum` + PG enum creation in the first migration
- [ ] **S** Alembic init + `env.py` wired to settings and metadata
- [ ] **S** Migration `0001_initial_schema` — hand-reviewed
- [ ] **S** Seed loader `app/jobs/seed.py` — idempotent upserts on `slug`, validates `source_url`
- [ ] **M** Seed data: 15 agro zones, districts, ~25 crops, 26+ diseases, treatments, ~40 commodities
- [ ] **S** `tests/integration/test_migrations.py` — upgrade → downgrade → upgrade
- [ ] **S** `tests/integration/test_constraints.py` — unique price key, price ordering check, partial unique phone

**Gate:** `alembic upgrade head` and `downgrade base` both clean on a fresh DB; seed re-runs produce identical row counts; the four "defining queries" from the design doc execute with expected plans (no seq scan on `mandi_prices` for the trend query).

---

## Phase 5 — Backend core & auth

**Goal:** a real user can register, log in, refresh, and manage farms — with roles enforced.

- [ ] **M** Error hierarchy + global handler → the documented error contract
- [ ] **M** `core/security.py` — Argon2id, JWT encode/decode, refresh hashing
- [ ] **M** `core/deps.py` — `get_db`, `current_user`, `require_role`
- [ ] **M** `modules/auth` — register, login, refresh (single-flight rotation), logout, password change
- [ ] **M** `modules/users` — me, farms CRUD, primary farm, admin user list/role change
- [ ] **S** Rate limiting on `/auth/*`
- [ ] **S** Audit log write on role change
- [ ] **M** `tests/api/test_auth.py` + `test_farms.py` — happy path, 401, 403, ownership isolation, conflict, rate limit
- [ ] **S** Pagination helper + `{data, meta}` envelope applied consistently

**Gate:** pytest green; the full curl sequence register → login → me → create farm → refresh → logout behaves exactly as `02-api-spec.md` says; a farmer token hitting an admin route gets 403; a second refresh with a rotated token returns `REFRESH_REUSED` and kills the family.

---

## Phase 6 — Mobile shell

**Goal:** a real phone, real login, real dashboard.

- [ ] **M** Expo app init (TS, expo-router), `app.json`, `eas.json`, path aliases
- [ ] **S** `src/api/client.ts` — token attach, 401 single-flight refresh, error mapping, timeouts
- [ ] **S** `openapi-typescript` codegen wired to the running API
- [ ] **M** Auth state (context + `expo-secure-store`), guarded routes, splash restore
- [ ] **M** S0, S1, S2, S3 screens per the screen-flow doc
- [ ] **M** T1 dashboard skeleton with real `/meta` + `/weather/current`, T5 profile
- [ ] **M** Design system: theme, Button, Card, Field, Chip, Skeleton, EmptyState, Banner
- [ ] **M** i18n bootstrap (en/hi), language persistence, RTL-safe layout
- [ ] **S** Error/empty/offline components used by every screen from here on

**Gate:** on a physical Android device via Expo Go: register → onboarding → dashboard with the district's real weather; kill and reopen the app → still logged in; turn on airplane mode → offline states, not crashes; switch language → whole app changes.

---

## Phase 7 — PLAN module

**Goal:** soil, weather and crop recommendation work end to end on real data.

- [ ] **M** `integrations/weather_openweather.py` — current + forecast, timeouts, retries, typed errors, normaliser
- [ ] **S** `integrations/weather_openmeteo.py` — fallback driver behind the same interface
- [ ] **M** Weather caching via `weather_snapshots` (TTL by kind)
- [ ] **M** Advisory rule engine + 8 rules + unit tests per rule
- [ ] **M** `modules/weather` — current, forecast, advisories
- [ ] **M** `modules/soil` — thresholds from crop data, `statuses` + `recommendations`, ruleset version
- [ ] **M** Soil reference content (how to read an SHC, what each nutrient does)
- [ ] **L** `modules/crops` — model load, feature assembly (soil + weather), rule layer (season, zone, rotation), reasons generator
- [ ] **M** `ml/crop_recommendation/train.py` + evaluation + joblib artefact + model card
- [ ] **M** P1, P2, P2b, P3, P3b screens
- [ ] **S** Cross-links: soil → recommendation, recommendation → market price

**Gate:** for a real Pune farm: weather matches a third-party source within tolerance; advisories fire correctly for a synthetic heavy-rain forecast (test) and are silent on a clear day; crop recommendation returns ≥ 3 ranked crops with reasons and suppresses out-of-zone crops; a re-request with modified soil changes the ranking; every number on screen traces to an API field.

---

## Phase 8 — PROTECT module

**Goal:** train, evaluate, serve and ship disease detection with honest confidence handling.

- [ ] **L** `ml/disease/train.py` — PlantVillage, leaf-grouped split, augmentation (field simulation), MobileNetV3/EfficientNet
- [ ] **M** `ml/disease/evaluate.py` — per-class P/R/F1, confusion matrix, calibration curve, field-photo set
- [ ] **M** `model_card.json` generation (version, metrics, dataset hash, date, known limitations)
- [ ] **S** `export_onnx.py` + parity test vs PyTorch logits
- [ ] **M** `ml/disease/predictor.py` — preprocess, top-k, leaf gate, confidence threshold
- [ ] **M** `modules/disease` — detect (upload validation), detections list/detail, escalate
- [ ] **S** Upload hardening: magic bytes, decompression-bomb guard, EXIF strip, re-encode, UUID keys
- [ ] **M** Storage integration (local driver, R2 driver + signed URLs)
- [ ] **M** `modules/disease` expert endpoints — queue, review (confirm/correct), audit log
- [ ] **M** Detection history + library screens
- [ ] **M** R1, R2, R3, R4 screens incl. uncertain/rejected states
- [ ] **S** `tests/unit/test_disease_contract.py` — uncertain path returns no treatments; label↔catalogue integrity

**Gate:** model card published with real measured numbers (lab and field set) — no invented metrics; ONNX parity within tolerance; a non-leaf photo returns `NO_LEAF_DETECTED`; a low-confidence photo returns `uncertain` with **zero** treatment content; expert correction writes audit log and leaves model output intact; end-to-end on device under 20 s on 3G.

---

## Phase 9 — SELL module

**Goal:** real AGMARKNET prices, ingested nightly, compared honestly.

- [ ] **M** `integrations/agmarknet.py` — paged fetch, filters, rate limit, retries, normaliser (state/district/market/commodity/variety/grade aliases)
- [ ] **M** Ingestion job → upsert, run record, row accounting, failure notification
- [ ] **S** Market/commodity/district upsert from ingested rows
- [ ] **M** `modules/markets` — prices, compare, trends, suggestions, msp, status
- [ ] **M** Nearest-mandi logic (Haversine), transport estimate with disclosed formula
- [ ] **M** MSP + crop calendar reference data with sources
- [ ] **M** M1, M2, M3, M4 screens
- [ ] **S** "No data for district" state with `nearest_with_data`
- [ ] **S** Verify licence/attribution requirements and add attribution to the app's Data sources screen

**Gate:** a real nightly run ingests ~10k+ rows with zero duplicates on re-run (idempotency proven by running twice); compare returns like-for-like variety/grade with `arrival_date`; trend gaps are gaps; `/markets/status` reports the last run honestly; simulated upstream failure leaves cached data served with `stale: true`.

---

## Phase 10 — Voice & multilingual

- [ ] **M** Bhashini client (ASR, NMT, TTS) with timeouts and graceful degradation
- [ ] **M** Intent router (7 allowed intents) + answer composer that reuses screen data
- [ ] **M** X3 voice modal, mic permission, 16 kHz recording, playback
- [ ] **S** `expo-speech` fallback when Bhashini is unavailable
- [ ] **M** Hindi translation pass over all keys; coverage check ≥ 95% enforced in CI
- [ ] **S** Accessibility pass: screen-reader labels, 200% font size, contrast

**Gate:** a Hindi voice question "आज मंडी भाव क्या है?" returns a spoken Hindi answer matching the price screen; the same for weather; unsupported intent is refused clearly; app works with Bhashini offline (fallback path) without a crash.

---

## Phase 11 — Admin & notifications

- [ ] **M** admin-web scaffold (Vite, router, auth, table primitives)
- [ ] **M** Detections queue + review UI (image beside model output)
- [ ] **M** Reference data CRUD with `source_url`/`last_verified` required
- [ ] **M** Ingestion page (run history, manual trigger, error detail), stats page
- [ ] **M** Notification model + in-app driver + dedupe + quiet hours
- [ ] **S** Alert rules: weather advisories, disease risk, price movement
- [ ] **M** SMS driver + DLT fields, behind `SMS_ENABLED`
- [ ] **M** X1 notifications screen, subscriptions UI
- [ ] **S** Expert reply → farmer notification → X2 thread

**Gate:** admin corrects a detection and the farmer sees the correction + notification; forecast-driven alert fires once (dedupe proven by re-running the job); with `SMS_ENABLED=false` the UI shows SMS as unavailable rather than failing silently.

---

## Phase 12 — Testing & hardening

- [ ] **M** Coverage ≥ 75% backend, 100% of rule functions, all endpoints contract-tested
- [ ] **S** `schemathesis` fuzz run against OpenAPI
- [ ] **M** Security pass: upload abuse, authz matrix sweep, rate limits, secret handling, dependency audit
- [ ] **M** Load test: 100 concurrent users on weather + prices, p95 targets met
- [ ] **S** Accessibility + low-end device check (2 GB Android, 200% font)
- [ ] **S** Failure drills: DB down, upstream down, model missing, disk full

**Gate:** documented results (including failures we chose not to fix, with reasons); no high-severity findings; endpoints degrade per the documented contract.

---

## Phase 13 — Deployment

- [ ] **M** Production `docker-compose.prod.yml` (no dev mounts, resource limits, restart policies)
- [ ] **M** nginx + TLS (Let's Encrypt), security headers, gzip, static admin build
- [ ] **M** Managed Postgres or volume-backed PG with daily `pg_dump` + offsite copy; **restore rehearsal**
- [ ] **S** Secrets via host env file, not in image; `.env` permissions
- [ ] **S** Monitoring: uptime check on `/healthz`, log aggregation, ingestion-failure alert, disk alert
- [ ] **S** EAS build for the Android APK; versioning + update channel
- [ ] **S** Runbook: deploy, rollback, restore, rotate keys

**Gate:** public HTTPS URL serving API + admin; a scheduled backup restored into a scratch DB successfully; a deliberate container kill recovers automatically.

---

## Phase 14 — Documentation & demo

- [ ] **S** README: setup from zero, in order, with verification steps
- [ ] **S** `docs/api.md` generated + annotated; `docs/data-sources.md` with licences and last-verified dates
- [ ] **M** Model cards published (disease, crop rec) incl. limitations
- [ ] **S** Demo script: 7 minutes, PLAN → PROTECT → SELL, incl. the uncertain-disease path
- [ ] **S** Known-limitations page in the app + README (lab-vs-field accuracy, daily not live prices, OTP/SMS status)

**Gate:** a fresh machine follows the README to a running stack without asking questions; the demo runs on a phone with no manual fixups.

---

## Critical path

```
3 Docker → 4 DB → 5 Auth → 6 Mobile shell ─┬→ 7 PLAN ─┐
                                           ├→ 8 PROTECT ─┼→ 12 Testing → 13 Deploy → 14 Docs
                                           └→ 9 SELL ──┘
                                                10 Voice (after 7+9)
                                                11 Admin/SMS (after 8+9)
```

Phases 7, 8 and 9 can be reordered, but **8 is the longest** (dataset, training, evaluation) — start the training run as soon as Phase 4 lands, in parallel with 5/6, so it isn't the critical path at the end.

## Standing definition of done (every task)

Code reviewed by yourself against the spec · tests added for new logic · no new lint/type errors · API changes reflected in `docs/api-spec` · new external data carries provenance · no mock data reachable without a visible badge · errors have a user-visible next step.

# Phase 2 — Architecture Decision Records

Short records of decisions that are expensive to reverse. Format: context → decision → consequences → alternatives rejected.

---

## ADR-001 — PostgreSQL as the only datastore

**Context.** Users, farms, detections, market prices and reference data are all relational, and SELL needs aggregation over time (trends, comparisons). Redis was considered for caching and job queuing.

**Decision.** PostgreSQL 16 holds everything. Redis is introduced only in Phase 11 for rate limiting and alert fan-out, never as a system of record.

**Consequences.** One backup story, one migration path, real joins for "nearby mandis" and "diseases for this crop". We accept that JSONB columns (`top_k`, `results`, `payload`) move some flexibility into the database, with typed columns for everything we query or index.

**Rejected.** MongoDB (no joins, and the data is not document-shaped); Redis-first (durability risk for price history, which is the product's own asset); SQLite (no concurrent writes with a worker, no window functions worth relying on in production).

---

## ADR-002 — Modular monolith, one deployable backend

**Context.** You explicitly ruled out microservices for the MVP. The domain has clear module boundaries (auth, soil, weather, crops, disease, markets).

**Decision.** A single FastAPI app with `app/modules/<module>/{router,schemas,service,models}.py`. Modules communicate through service functions. Cross-cutting concerns (db, auth, errors, storage) live in `app/core` and `app/integrations`. A separate worker process handles nightly ingestion.

**Consequences.** One container to deploy, one OpenAPI document, one test run. Module boundaries are enforced by convention and review, not by the network — so discipline is required: no module imports another module's router, and shared logic goes to `core` or a service, never copy-pasted. If a module later needs independent scaling (disease inference is the only candidate), it can be extracted behind the same service interface because the API layer already doesn't know how inference is produced.

**Rejected.** Microservices (operational cost, network failure modes, distributed transactions for no benefit at this scale); a single flat `routes/` folder (this project has too many domains for that to stay readable past Phase 8).

---

## ADR-003 — Python 3.12 + FastAPI, not Node

**Context.** The ML work (PyTorch, scikit-learn) is Python. The app is otherwise a typical CRUD + integrations API.

**Decision.** FastAPI with Pydantic v2, SQLAlchemy 2.0 async, Alembic. Python pinned to 3.12 (the dev machine has 3.14, which lacks ML wheel support).

**Consequences.** No model-serving bridge, no second runtime, shared types between training and inference code. Async is used for I/O (upstream APIs), with CPU-bound inference offloaded to a thread pool so it doesn't block the event loop. Pydantic gives request validation and typed OpenAPI for free.

**Rejected.** Node/NestJS + a Python inference service (two languages, two deploy units, a serialisation boundary); Django (built-in admin is tempting but DRF + Django is heavier than needed here, and async is second-class); Flask (no validation or OpenAPI without bolting on two more libraries).

---

## ADR-004 — JWT access tokens + rotating refresh tokens, phone + password

**Context.** Mobile client, low-connectivity users, no reliable email. OTP login requires SMS, which requires DLT registration (slow, external).

**Decision.** Phone + password now. Access JWT (15 min) + opaque refresh token (7 days, rotated, reuse detection). Argon2id hashes. OTP endpoints exist but return `501` until Phase 11.

**Consequences.** No SMS dependency for the core product. Password entry is a real usability cost for low-literacy users — mitigated by large numeric keypads and a visible `+91`, and by planning OTP as the future default rather than a nice-to-have. Refresh rotation means a stolen token has a bounded life and reuse is detectable.

**Rejected.** Cookie sessions (awkward in React Native, needs CSRF handling for the web admin); long-lived JWTs (no revocation); OTP-only at MVP (blocked on DLT paperwork); social login (wrong audience).

**Update (2026-11-23).** Revisited: OTP is now implemented as the primary sign-in path, with password kept as a fallback. Delivered without the DLT blocker by running in `dev` mode (no SMS, code returned only outside production) behind the same adapter used by MSG91/Fast2SMS. The security properties above still hold: the OTP flow issues the same access/refresh pair. OTP-only accounts have a null password hash.

---

## ADR-005 — ONNX for disease inference, PyTorch only for training

**Context.** The model must run on a cheap CPU container; training happens on Colab/Kaggle GPU.

**Decision.** Train with PyTorch + `timm` (MobileNetV3 / EfficientNet-B0), export to ONNX, serve with `onnxruntime` in the API image. Training deps never enter the production image.

**Consequences.** Serving image stays ~200 MB smaller without `torch`, and CPU inference is faster and more predictable. Cost: two environments to keep consistent, and ONNX must be validated against PyTorch outputs (a numeric parity test in Phase 8 — differences beyond tolerance fail the build). Model artefacts are versioned with a `model_card.json` and checksummed at load.

**Rejected.** Serving PyTorch directly (heavier image, slower cold start); a separate TorchServe/Triton container (another service for one small model); TF Serving (same, plus a second framework).

---

## ADR-006 — Storage abstraction with a local driver

**Context.** Images must be stored, but development should not require cloud credentials, and production should not use local disk.

**Decision.** `StorageProvider` interface (`put`, `get_signed_url`, `delete`) with `LocalStorage` and `R2Storage` implementations, chosen by env var. Local disk is served by the API in dev only; R2 is used in staging/production.

**Consequences.** `docker compose up` works on a fresh machine with no accounts. The contract is small enough that a third driver (S3, B2) is a 60-line class. We must keep metadata (key, content type, size) in Postgres because local disk and R2 behave differently on overwrite and public access.

**Rejected.** Writing directly to S3 SDK calls everywhere (untestable, credential-locked); storing image bytes in Postgres (bloats backups, kills query performance).

---

## ADR-007 — Ingest AGMARKNET into our own tables; never call it in a request

**Context.** data.gov.in serves a daily snapshot, ~1,000 rows/page, with publication lag and per-mandi sparsity. It is rate-limited by API key and occasionally slow.

**Decision.** A nightly worker pulls, normalises and upserts into `mandi_prices`, recording a `price_ingestion_runs` row. The API reads only from Postgres. `arrival_date` and `ingested_at` are both stored and both returned.

**Consequences.** Screens stay fast and keep working when the upstream is down. We own the price history, which is what makes trends possible at all. The cost is a job that can fail silently — so ingestion health is exposed at `/markets/status`, in `/meta`, and in the admin panel, and a failed run raises an in-app admin notification rather than vanishing into logs.

**Rejected.** Proxy the upstream per request (slow, quota-hungry, breaks under load); trusting upstream "live" framing (it is not live, and presenting it as such would be misleading).

---

## ADR-008 — Deterministic rules instead of an LLM for agronomic advice

**Context.** The platform gives advice about chemicals and money. An LLM could generate fluent, plausible, wrong text.

**Decision.** All agronomic advice is either (a) curated reference data with `source_url` and `last_verified`, or (b) a deterministic, unit-tested rule (`rule_id` returned in the response). No LLM in the advice path.

**Consequences.** Every claim is traceable and testable; a rule change is reviewable in a diff. Coverage is narrower than an LLM's — we must curate disease treatments, crop calendars and advisories by hand and keep them current. Accepted deliberately: for dosage and safety, traceability beats fluency.

**Rejected.** LLM-generated treatment text (hallucination risk on dosages, no provenance); RAG over unverified web content (same risk with extra steps).

---

## ADR-009 — Honest confidence handling in PROTECT, including a "we don't know" state

**Context.** PlantVillage images are lab conditions; field accuracy will be lower. A confident wrong diagnosis leads to wasted money and possibly crop loss.

**Decision.** Show top-3 with confidences. Below `DISEASE_CONFIDENCE_THRESHOLD` return `status=uncertain` with **no predicted disease and no treatments**, plus an expert path. A leaf gate rejects non-leaf inputs. Every result carries a disclaimer and an escalation option. Model version is stored per detection.

**Consequences.** Some users get "we're not sure" where a naive app would have shown a wrong answer — this is intended. Requires an expert workflow to exist before launch, otherwise the uncertain state dead-ends; that is why escalation is Phase 8, not Phase 11.

**Rejected.** Always returning a top-1 answer (misleading); showing treatments regardless of confidence (safety hazard); hiding confidence (users then treat the answer as certain).

---

## ADR-010 — SMS is architected now, delivered later behind a flag

**Context.** India requires DLT registration (entity, header, template approval) before any SMS is delivered. TIMELINE is external and slow; SMS also has DND/quiet-hour rules.

**Decision.** Build `NotificationChannel` with `in_app` and `console` drivers at MVP; the SMS driver (MSG91/Fast2SMS) ships behind `SMS_ENABLED=false` and is enabled once DLT approval lands. Quiet hours are part of the subscription model from the start.

**Consequences.** No feature is blocked on paperwork. The risk is shipping a "SMS notifications" toggle that does nothing — so the UI shows SMS as unavailable (not enabled-but-silent) until the flag is on, and `/meta.features.sms` drives that.

**Rejected.** Choosing an international SMS API to dodge DLT (delivery to Indian numbers will be blocked or unreliable); pretending SMS works in the demo (dishonest, and it hides the real blocker).

---

## ADR-011 — English + Hindi first, others as translation files

**Context.** The brief asks for Hindi, English and regional languages. Maintaining 10 languages at once splits effort and produces half-translated screens.

**Decision.** Two complete locales at MVP; `language_code` enum already contains the rest so adding a language is a JSON file + a QA pass, not a migration.

**Consequences.** Regional coverage is deferred, and we must resist shipping a half-translated language (the picker is gated on ≥ 95% key coverage). Reference content (diseases, advisories) carries `_hi` columns for the same reason — adding `_mr` later means a migration, which is accepted for content that must be human-reviewed anyway.

**Rejected.** Auto-translating the UI at runtime (cost, latency, inconsistent terminology); shipping 6 languages at 60% coverage (looks broken, erodes trust).

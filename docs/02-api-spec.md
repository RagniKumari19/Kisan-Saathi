# Phase 2 — API Specification

**Base URL:** `https://<host>/api/v1` · **Format:** JSON (UTF-8) except uploads · **Docs:** auto-generated OpenAPI at `/api/docs` (Swagger) and `/api/openapi.json`
**Status:** Contract for Phases 5–11. Endpoints are built in the phase noted in the last column.

---

## 1. Conventions

| Topic | Rule |
|---|---|
| Versioning | Path-based `/api/v1`. Breaking change → `/api/v2`. Additive fields are not breaking and do not bump the version |
| IDs | UUIDv4 strings |
| Timestamps | ISO-8601 UTC with `Z`, millisecond precision (`2026-11-22T09:14:03.512Z`) |
| Dates (no time) | `YYYY-MM-DD` |
| Money | number, ₹ per quintal, 2 decimals (`2450.00`) — never a string, never in paise |
| Lists | `{ "data": [...], "meta": { "page": 1, "limit": 20, "total": 137, "has_next": true } }` |
| Single object | `{ "data": { ... } }` |
| Errors | `{ "error": { "code": "...", "message": "...", "details": [...], "request_id": "..." } }` |
| Request tracing | Every response carries `X-Request-ID` (echoed if client supplied one) |
| Naming | `snake_case` in JSON, matching the DB columns |
| Null vs absent | Absent means "not requested/not applicable"; `null` means "known to be unavailable". Never `""` for missing numbers |
| Caching | `Cache-Control: private, max-age=N` on reference data; `no-store` on anything user-specific |
| Idempotency | `POST /disease/detect` accepts optional `Idempotency-Key`; a repeat within 24 h returns the original detection |

**Absolute rule for external data:** every response that contains third-party data carries provenance:

```json
"provenance": {
  "source": "agmarknet",
  "source_url": "https://agmarknet.gov.in",
  "retrieved_at": "2026-11-22T02:10:44.000Z",
  "data_date": "2026-11-21",
  "is_mock": false,
  "stale": false
}
```
`is_mock: true` is set by any mock driver and rendered as a visible badge in the app. `stale: true` when `retrieved_at` is older than the expected refresh window.

---

## 2. Authentication & authorisation

- **Login:** phone + password (`POST /auth/login`). OTP endpoints exist in the contract but return `501 NOT_IMPLEMENTED` until SMS/DLT is live (Phase 11) — an honest placeholder rather than a fake flow.
- **Tokens:** access JWT, 15 min, HS256, claims `{ sub, role, lang, iat, exp, jti }`. Refresh token opaque, 7 days, rotated on every use; reuse of a rotated token revokes the whole family.
- **Transport:** access token in `Authorization: Bearer <token>`. Refresh token in the body only (mobile stores it in `expo-secure-store`).
- **Authorisation:** server-side only, via `require_role(...)` dependencies. The role matrix below is the full permission surface; anything unlisted is `403`.

| Capability | farmer | expert | admin |
|---|---|---|---|
| Own profile / farms / soil / detections / recommendations | ✅ | ✅ | ✅ |
| Read market + weather + crop data | ✅ | ✅ | ✅ |
| Escalate a detection to an expert | ✅ own | ✅ | ✅ |
| View expert queue, review any detection | ❌ | ✅ | ✅ |
| View any user's data | ❌ | detections + consultations only | ✅ |
| Change roles, edit reference data, run ingestion | ❌ | ❌ | ✅ |

---

## 3. Error contract

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "One or more fields are invalid.",
    "details": [{ "field": "ph", "issue": "must be between 0 and 14" }],
    "request_id": "6f1c0b0a-8c2e-4f2a-9b4c-1d5f8e7a2b31"
  }
}
```

| HTTP | `code` | Meaning | Client behaviour |
|---|---|---|---|
| 400 | `VALIDATION_ERROR` | Field-level validation failed | Show inline errors |
| 401 | `AUTH_REQUIRED` | Missing/invalid access token | Try refresh once, then log out |
| 401 | `INVALID_CREDENTIALS` | Wrong phone/password | Show message, no hint which was wrong |
| 401 | `TOKEN_EXPIRED` | Access token expired | Refresh silently |
| 401 | `REFRESH_REUSED` | Rotated refresh token reused | Force logout, clear storage |
| 403 | `FORBIDDEN` | Role cannot do this | Hide the action in UI |
| 404 | `NOT_FOUND` | Resource absent or not owned by caller | Do not leak existence |
| 409 | `CONFLICT` | Duplicate phone/email, farm already primary | Field-specific message |
| 413 | `PAYLOAD_TOO_LARGE` | Image > 8 MB | Compress and retry |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Not a real image (magic-byte check) | Re-capture |
| 422 | `IMAGE_UNREADABLE` | Decoded but unusable (too small, corrupt) | Re-capture with guidance |
| 422 | `NO_LEAF_DETECTED` | Leaf gate rejected the crop | Show "we couldn't see a leaf" |
| 429 | `RATE_LIMITED` | Limit exceeded; `Retry-After` header set | Back off |
| 502 | `UPSTREAM_UNAVAILABLE` | Weather/mandi provider failed | Show cached data + stale badge |
| 503 | `MODEL_UNAVAILABLE` | Model artifact not loaded | Disable PROTECT, explain |
| 501 | `NOT_IMPLEMENTED` | Contract exists, feature not built yet | Hide the feature |

Degradation policy: weather and mandi prices **never** hard-fail a screen if we hold any cached data for that location — return the cache with `stale: true` and an advisory note. If we hold nothing, return `502` and the UI shows an explicit "data unavailable" state, never a blank table.

---

## 4. Rate limits

Per user when authenticated, per IP otherwise. `429` + `Retry-After`.

| Endpoint group | Limit |
|---|---|
| `/auth/login`, `/auth/register` | 5 / 15 min per IP, 10 / hour per phone |
| `/auth/refresh` | 60 / hour |
| `/disease/detect` | 20 / hour, 100 / day (compute cost) |
| `/crops/recommend` | 30 / hour |
| Weather endpoints | 60 / hour per user (cache makes this effectively free) |
| Everything else | 300 / hour |

---

## 5. Endpoint reference

### 5.1 System

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/healthz` | none | Liveness; `{status, version, uptime_s}` |
| GET | `/readyz` | none | DB + model + storage readiness; `503` if not ready |
| GET | `/meta` | none | App version, `model_versions`, `data_freshness` per source, enabled features |

`/meta` is what lets the mobile app show honest freshness badges and hide unbuilt features:

```json
{ "data": {
  "app_version": "0.6.0",
  "model_versions": { "disease": "disease-mnv3-v1", "crop_rec": "croprec-gb-v1" },
  "data_freshness": { "agmarknet": "2026-11-21", "weather_cache": "2026-11-22T09:05:00Z" },
  "features": { "voice": false, "sms": false, "otp_login": false, "expert_review": true }
} }
```

### 5.2 Auth — Phase 5

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/auth/register` | none | phone, password, full_name, language; returns tokens + user |
| POST | `/auth/login` | none | phone, password → tokens + user |
| POST | `/auth/refresh` | none | refresh_token → new pair (rotation) |
| POST | `/auth/logout` | bearer | revokes presented refresh token |
| PATCH | `/auth/password` | bearer | current + new password; revokes all other sessions |
| POST | `/auth/otp/request` | none | `501` until Phase 11 |
| POST | `/auth/otp/verify` | none | `501` until Phase 11 |

```http
POST /api/v1/auth/register
{ "phone": "+919876543210", "password": "…", "full_name": "Ramesh Patil", "language": "hi" }

201 Created
{ "data": {
    "user": { "id": "…", "phone": "+919876543210", "full_name": "Ramesh Patil",
              "role": "farmer", "language": "hi", "created_at": "2026-11-22T09:14:03.512Z" },
    "tokens": { "access_token": "…", "refresh_token": "…", "token_type": "bearer", "expires_in": 900 }
} }
```
Password policy: ≥ 8 chars, not in a common-password list, not equal to the phone. Errors are field-specific but the response time is constant (no user enumeration).

### 5.3 Users & farms — Phase 5

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/users/me` | bearer | profile + primary farm summary |
| PATCH | `/users/me` | bearer | full_name, language |
| GET | `/users/me/farms` | bearer | own farms |
| POST | `/users/me/farms` | bearer | first farm auto-becomes primary |
| GET | `/users/me/farms/{farm_id}` | bearer | |
| PATCH | `/users/me/farms/{farm_id}` | bearer | |
| DELETE | `/users/me/farms/{farm_id}` | bearer | `409` if it is the only farm |
| POST | `/users/me/farms/{farm_id}/primary` | bearer | demotes the previous primary |
| GET | `/users` | admin | paginated, `?role=&q=` |
| PATCH | `/users/{user_id}/role` | admin | audited |

```json
POST /api/v1/users/me/farms
{ "name": "Wagh farm", "district_id": "…", "village": "Shirur",
  "latitude": 18.5223, "longitude": 74.1187, "area_acres": 3.5,
  "soil_type": "black", "irrigation_source": "borewell" }
```

Validation: lat `-90..90`, lon `-180..180`; `area_acres > 0`; `district_id` must exist; max 10 farms per user.

### 5.4 PLAN — soil — Phase 7

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/soil/reports` | bearer | save a report without analysis |
| GET | `/soil/reports` | bearer | `?farm_id=` history, newest first |
| GET | `/soil/reports/{id}` | bearer | |
| POST | `/soil/analyze` | bearer | save + interpret (+ optional `crop_slug`) |

```json
POST /api/v1/soil/analyze
{ "farm_id": "…", "crop_slug": "cotton", "tested_on": "2026-11-10", "source": "manual",
  "nitrogen_kg_ha": 210, "phosphorus_kg_ha": 18, "potassium_kg_ha": 320,
  "ph": 8.1, "organic_carbon_pct": 0.42, "ec_ds_m": 0.31 }

201 Created
{ "data": {
  "report_id": "…",
  "analysis": {
    "statuses": { "nitrogen": "medium", "phosphorus": "low", "potassium": "high",
                  "ph": "moderately_alkaline", "organic_carbon": "low" },
    "summary_en": "Your soil is low in phosphorus and organic carbon, and slightly alkaline for cotton.",
    "recommendations": [
      { "priority": 1, "action": "Add organic matter",
        "detail": "Apply 4–5 tonnes/acre well-rotted FYM before sowing to raise organic carbon.",
        "source_url": "https://…" },
      { "priority": 2, "action": "Correct phosphorus",
        "detail": "Apply DAP 50 kg/acre at sowing; do not exceed the dose on the package.",
        "source_url": "https://…" }
    ],
    "ruleset_version": "soil-rules-v1",
    "disclaimer": "General guidance based on your test values. Confirm doses with your local Krishi Vigyan Kendra."
  }
} }
```
Every recommendation carries `source_url` (schema-enforced). Missing input fields yield `null` status, not a guess: `"statuses": { "potassium": null }` with a note listing what to test next.

### 5.5 PLAN — weather — Phase 7

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/weather/current?farm_id=` | bearer | current conditions |
| GET | `/weather/forecast?farm_id=&days=5` | bearer | normalised 3-hour slots + daily summary; `days` 1–5 |
| GET | `/weather/advisories?farm_id=` | bearer | rule-derived advisories with `rule_id` |

```json
GET /api/v1/weather/forecast?farm_id=…&days=3
{ "data": {
  "location": { "latitude": 18.5223, "longitude": 74.1187, "district": "Pune" },
  "daily": [
    { "date": "2026-11-23", "temp_min_c": 15.2, "temp_max_c": 29.8,
      "humidity_pct": 78, "rain_mm": 0.0, "wind_kmph": 12,
      "condition": "partly_cloudy", "icon": "02d" }
  ],
  "advisories": [
    { "rule_id": "spray_window_ok", "severity": "info",
      "title_en": "Good spraying window", "title_hi": "…",
      "detail_en": "Low wind and no rain expected for 24 hours.",
      "valid_until": "2026-11-24T06:00:00.000Z" },
    { "rule_id": "fungal_risk_high", "severity": "warning",
      "title_en": "High fungal disease risk",
      "detail_en": "Humidity above 85% with 20–30 °C for 2 days. Check leaves for spots." }
  ],
  "provenance": { "source": "openweathermap", "retrieved_at": "…", "data_date": "2026-11-22", "is_mock": false, "stale": false },
  "disclaimer": "Advisories are generated from forecast data by this app, not official government warnings."
} }
```
Rule IDs are stable and unit-tested (`spray_window_ok`, `spray_window_bad`, `frost_warning`, `heat_stress`, `heavy_rain_24h`, `irrigation_deficit_hint`, `fungal_risk_high`, `windy_no_spray`). Advisories are deterministic functions of the forecast — no LLM, no invented alerts.

### 5.6 PLAN — crops — Phase 7

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/crops` | none | catalogue, `?season=&zone=` |
| GET | `/crops/{slug}` | none | detail + calendar windows |
| POST | `/crops/recommend` | bearer | ML + rules, returns ranked list |
| GET | `/crops/recommendations` | bearer | `?farm_id=` history |
| GET | `/crops/recommendations/{id}` | bearer | stored result, reproducible |

```json
POST /api/v1/crops/recommend
{ "farm_id": "…", "season": "rabi" }

201 Created
{ "data": {
  "id": "…",
  "model_version": "croprec-gb-v1",
  "input_features": { "n": 210, "p": 18, "k": 320, "temperature": 24.1,
                      "humidity": 61, "ph": 8.1, "rainfall": 12.4,
                      "rainfall_source": "forecast_30d" },
  "results": [
    { "crop_slug": "chickpea", "name_en": "Chickpea", "name_hi": "…",
      "probability": 0.41, "confidence_band": "medium",
      "reasons": ["pH 8.1 suits chickpea", "Low rainfall expected in rabi", "Medium nitrogen requirement"],
      "agro_zone_ok": true,
      "yield_range": null,
      "yield_note": "Yield estimate not available for this crop and district." },
    { "crop_slug": "wheat", "probability": 0.27, "confidence_band": "medium", "…": "…" }
  ],
  "suppressed": [ { "crop_slug": "apple", "reason": "Not recommended in your agro-climatic zone" } ],
  "provenance": { "source": "ml_model", "model_version": "croprec-gb-v1",
                  "training_data": "Kaggle crop-recommendation-dataset (synthetic, augmented)",
                  "is_mock": false, "stale": false },
  "disclaimer": "Suggestion based on soil values, weather and crop rules. Not a guarantee of yield. Confirm with your agriculture officer."
} }
```
Contract details that matter:
- `results` is **always** a ranked list (≥ 3 unless the rule layer suppresses everything, in which case `results: []` + `explanation`).
- `probability` is model output; `confidence_band` is a coarse calibrated label. They are not the same thing and the UI shows the band as text.
- `suppressed` is returned so the UI can explain *why* a crop the farmer asked about is missing.
- `yield_range: null` until a validated yield model exists. `null` is a feature.

### 5.7 PROTECT — disease — Phase 8

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/disease/detect` | bearer | multipart image; synchronous inference |
| GET | `/disease/detections` | bearer | own history, `?farm_id=&crop_slug=` |
| GET | `/disease/detections/{id}` | bearer | |
| POST | `/disease/detections/{id}/escalate` | bearer | creates a consultation, sets `review_status=pending_expert` |
| GET | `/disease/queue` | expert/admin | pending reviews, oldest first |
| PATCH | `/disease/detections/{id}/review` | expert/admin | `{decision: confirmed\|corrected, disease_slug?, note}`; audited |
| GET | `/disease/library` | none | disease catalogue `?crop_slug=` |
| GET | `/disease/library/{slug}` | none | symptoms, spread, treatments |
| GET | `/disease/risk-alerts?farm_id=` | bearer | weather-linked risk for the farm's crop |

**Upload contract:** `multipart/form-data` with `image` (JPEG/PNG/WebP, ≤ 8 MB, ≥ 224×224), optional `farm_id`, `crop_slug`, `Idempotency-Key` header.
Server validation: sniff magic bytes (ignore client `Content-Type`), decode with Pillow in a size-limited session (decompression-bomb guard), re-encode to strip EXIF, store under a random UUID, hash with SHA-256.

```json
POST /api/v1/disease/detect   (multipart)
201 Created
{ "data": {
  "id": "…",
  "status": "completed",
  "predicted": { "slug": "tomato__early_blight", "name_en": "Early blight",
                 "name_hi": "…", "confidence": 0.71, "pathogen_type": "fungal" },
  "top_k": [
    { "slug": "tomato__early_blight", "name_en": "Early blight", "confidence": 0.71 },
    { "slug": "tomato__late_blight",  "name_en": "Late blight",  "confidence": 0.19 },
    { "slug": "tomato__leaf_mold",    "name_en": "Leaf mold",    "confidence": 0.06 }
  ],
  "severity": 3,
  "symptoms_en": "Brown spots with concentric rings on lower leaves…",
  "treatments": [
    { "kind": "cultural", "title": "Remove infected leaves",
      "detail": "…", "source_url": "https://…", "last_verified": "2026-10-02" },
    { "kind": "chemical", "title": "Mancozeb 75% WP", "dosage": "2 g/L water",
      "safety_notes": "Wear gloves; 7-day pre-harvest interval.",
      "source_url": "https://…", "last_verified": "2026-10-02" }
  ],
  "model": { "name": "mobilenetv3_large", "version": "disease-mnv3-v1" },
  "latency_ms": 412,
  "image_key": "detections/2026/11/<uuid>.jpg",
  "provenance": { "source": "ml_model", "is_mock": false, "stale": false },
  "disclaimer": "This is an AI estimate, not a diagnosis. Confirm with your Krishi Mitra before spending on chemicals.",
  "next_actions": ["escalate_to_expert", "view_library"]
} }
```

Uncertain / rejected shapes (these are first-class responses, not errors):

```json
{ "data": {
  "id": "…", "status": "uncertain", "predicted": null,
  "top_k": [ { "slug": "tomato__early_blight", "confidence": 0.34 },
             { "slug": "tomato__late_blight", "confidence": 0.29 } ],
  "message_en": "The photo is unclear or the symptoms don't match strongly. Take another photo in daylight with one leaf filling the frame, or send it to an expert.",
  "next_actions": ["retake", "escalate_to_expert"]
} }
```
- `status: "rejected"` → `NO_LEAF_DETECTED` semantics, `top_k` omitted.
- `status: "uncertain"` → no `predicted`, no treatments shown. **The UI must not render chemical advice for an uncertain result.** That is a safety property, not a styling choice.
- Threshold is a config value (`DISEASE_CONFIDENCE_THRESHOLD`, default 0.55) and is recorded per detection via the model version + config snapshot in the response.

**Review contract:** expert `PATCH` with `decision: "corrected"` requires `disease_slug`; it writes `expert_id`, `expert_note`, `reviewed_at`, sets `status: "completed"`, and appends an `audit_logs` row. The original model output is never overwritten — `top_k` and `predicted_disease_id` remain as the model produced them, with the expert verdict in the review fields. Corrections become training data later without destroying evidence.

### 5.8 SELL — markets — Phase 9

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/markets` | none | `?state=&district_id=&q=` |
| GET | `/markets/prices` | none | `?commodity=&district_id=&state=&date=&variety=&grade=&page=` |
| GET | `/markets/compare` | none | same commodity across mandis, latest available day per market |
| GET | `/markets/trends` | none | `?commodity=&district_id=&days=90` daily averages |
| GET | `/markets/suggestions?farm_id=` | bearer | ranked by modal price net of estimated transport |
| GET | `/markets/msp` | none | curated MSP table with effective dates |
| GET | `/markets/status` | none | ingestion health: last successful run, row counts, staleness |

```json
GET /api/v1/markets/compare?commodity=onion&district_id=…&radius_km=80
{ "data": {
  "commodity": { "slug": "onion", "name_en": "Onion" },
  "unit": "quintal",
  "markets": [
    { "market_id": "…", "market_name": "Pune (Gultekdi)", "district": "Pune",
      "distance_km": 12.4, "arrival_date": "2026-11-21",
      "min_price": 1200.00, "max_price": 2100.00, "modal_price": 1750.00,
      "variety": "Local", "grade": "FAQ",
      "net_after_transport": 1693.40, "transport_note": "Estimated: 12.4 km × ₹4.56/km/quintal" },
    { "market_id": "…", "market_name": "Shirur", "district": "Pune",
      "distance_km": 34.1, "arrival_date": "2026-11-20", "modal_price": 1890.00,
      "transport_note": "…" }
  ],
  "provenance": { "source": "agmarknet",
                  "source_url": "https://agmarknet.gov.in",
                  "retrieved_at": "2026-11-22T02:10:44.000Z",
                  "data_date": "2026-11-21", "is_mock": false, "stale": false },
  "notes": ["Prices are per quintal, as reported by each mandi on the date shown.",
            "Not every mandi reports every day.",
            "Transport cost is an estimate, not a quote."]
} }
```

Contract rules for SELL:
- `arrival_date` is mandatory in every price object and must be rendered.
- Rows are never mixed across varieties/grades silently: either filter, or return them as separate entries with `variety`/`grade` visible.
- `modal_price` is never labelled "average price" — it is the most common price, and the UI says so on first use.
- `net_after_transport` is only present when a distance exists; the formula and rate are disclosed in `transport_note`.
- If the requested district has no rows for that commodity, return `data.markets: []` with `meta.reason: "NO_DATA_FOR_DISTRICT"` and `meta.nearest_with_data: [...]` — a blank screen is a failure mode we design out.

### 5.9 Voice — Phase 10

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/voice/query` | bearer | multipart `audio` (≤ 30 s, 16 kHz mono) or JSON `{text, language}` → intent → answer text + optional TTS audio URL |

Allowed intents only: `weather_today`, `weather_forecast`, `mandi_price`, `mandi_best_market`, `crop_recommendation_summary`, `disease_help`, `help`. Anything else returns `intent: "unsupported"` with spoken guidance. No open-ended generation: the answer is assembled from the same data the screens show, then translated. This keeps the voice path from ever inventing a price or a dosage.

### 5.10 Notifications — Phase 11

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/notifications` | bearer | `?unread_only=&category=` |
| PATCH | `/notifications/{id}/read` | bearer | |
| POST | `/notifications/read-all` | bearer | |
| GET | `/notifications/subscriptions` | bearer | |
| PATCH | `/notifications/subscriptions` | bearer | per category + channel, respects quiet hours |

### 5.11 Admin — Phase 11

| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/admin/stats` | admin | users, detections/day, ingestion success rate, top crops |
| GET | `/admin/ingestion-runs` | admin | run history incl. failures |
| POST | `/admin/ingestion-runs` | admin | trigger a manual pull, `?date=` |
| GET/POST/PATCH | `/admin/reference/{resource}` | admin | `crops`, `crop_diseases`, `disease_treatments`, `commodities`, `msp_rates`, `crop_calendar` |
| GET | `/admin/audit-logs` | admin | `?entity=&actor_id=` |

Reference edits require `source_url` + `last_verified` on the payload; the API rejects rows without them (`VALIDATION_ERROR`), mirroring the DB constraint.

---

## 6. Mock vs real: how mocks are allowed to exist

A mock is permitted **only** behind the integration interface, **only** when the corresponding env var is absent, and it always:

1. sets `provenance.is_mock: true`,
2. logs `WARN mock_driver_active provider=<name>` at startup and on every use,
3. is refused when `APP_ENV=production` (startup fails fast instead of shipping plausible-looking fake data).

Mocks are never returned for the leading data path once real credentials exist. `tests/` may use fixtures freely; those never reach a running app.

---

## 7. Client strategy

- OpenAPI is generated by FastAPI; `openapi-typescript` produces `mobile/src/api/schema.d.ts`, so a backend field rename breaks the mobile build — a compile error instead of a runtime `undefined`.
- One `apiClient` per app: attaches the token, retries `401` once via refresh (single-flight), maps `error.code` to typed exceptions, honours `Retry-After`.
- Uploads: client-side resize to ≤ 1600 px longest edge, JPEG q80 — saves bandwidth on 3G and matches the model's 224 px input after server-side centre crop.
- Timeouts: 10 s default, 30 s for `/disease/detect`. Offline: cache last successful payloads for read-only screens; writes queue is out of scope for the MVP (explicit limitation).

---

## 8. Contract tests (Phase 12 gate)

`tests/api/` asserts, per endpoint: happy path, auth missing, wrong role, validation failure, ownership isolation (user A cannot read user B's detection → `404`), pagination meta, and the exact error `code`. `schemathesis` runs property-based fuzzing against the OpenAPI schema in CI. Any endpoint whose response diverges from this document is a bug in the endpoint, not in the document.

# Phase 2 — Database Design

**Target:** PostgreSQL 16 · SQLAlchemy 2.0 (async) · Alembic
**Status:** Design approved → implemented in Phase 4. This document is the source of truth for the schema.

---

## 1. Conventions

| Topic | Rule |
|---|---|
| Primary keys | `id UUID DEFAULT gen_random_uuid()` (built into PG13+) |
| Foreign keys | `<entity>_id UUID NOT NULL` + explicit `ON DELETE` per relationship |
| Timestamps | `timestamptz` (UTC), `created_at` default `now()`, `updated_at` maintained by a trigger-free `onupdate` in SQLAlchemy |
| Money | `NUMERIC(10,2)` — ₹ per quintal. Never float: floating point ruins price comparisons |
| Measurements | `NUMERIC` with explicit precision (soil values, lat/lon `NUMERIC(9,6)`) |
| Enums | Native PG enums, created via Alembic, mirrored as Python `enum.StrEnum` |
| Soft delete | Only `users` (`deleted_at`). Everything else is hard-deleted, cascading from the user |
| Naming | snake_case, plural tables, singular columns, `idx_`/`uq_`/`ck_`/`fk_` prefixes via SQLAlchemy naming convention |
| Text | `citext` for email; phone stored normalised E.164 (`+919876543210`) |

Alembic naming convention (set once in `db/base.py`, so migrations are stable and reversible):

```python
convention = {
  "ix": "ix_%(table_name)s_%(column_0_N_name)s",
  "uq": "uq_%(table_name)s_%(column_0_N_name)s",
  "ck": "ck_%(table_name)s_%(constraint_name)s",
  "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
  "pk": "pk_%(table_name)s",
}
```

---

## 2. Entity–relationship map

```
                        ┌──────────────┐
                        │  agro_zones  │ (reference: 15 ICAR zones)
                        └──────┬───────┘
                               │ code
                        ┌──────▼───────┐          ┌───────────────┐
                        │  districts   │◄─────────│    markets    │
                        │ state,name,  │          │ state,district│
                        │ zone,lat/lon │          │ name, lat/lon │
                        └──┬────────┬──┘          └───────┬───────┘
                           │        │                     │
                    ┌──────▼──┐     │              ┌──────▼────────┐
   ┌──────────┐     │  farms  │     │              │ mandi_prices  │◄── price_ingestion_runs
   │  users   │────<│         │     │              │ (unique per   │
   │ role,lang│ 1:N └──┬───┬──┘     │              │ market+comm+  │
   └──┬────┬──┘        │   │        │              │ variety+grade │
      │    │           │   │        │              │ +arrival_date)│
      │    │      ┌────▼───▼──┐     │              └──────▲────────┘
      │    │      │soil_reports│    │                     │
      │    │      └────┬───────┘    │              ┌──────┴────────┐
      │    │           │            │              │  commodities  │
      │    │      ┌────▼───────┐    │              └──────▲────────┘
      │    │      │soil_analyses│   │                     │
      │    │      └────────────┘    │              ┌──────┴────────┐
      │    │                        │              │   msp_rates   │
      │    │  ┌─────────────────────┴───┐          └───────────────┘
      │    └─<│ crop_recommendations    │
      │       └─────────────────────────┘
      │       ┌─────────────┐   ┌──────────────┐
      ├──────<│  detections │──<│ consultations│>──┐ (expert answers)
      │       └──┬───────┬──┘   └──────────────┘   │
      │          │       │                          │
      │    ┌─────▼────┐  └──► crop_diseases ──< disease_treatments
      │    │  farms   │            ▲
      │    └──────────┘            │
      │                      ┌─────┴────┐
      │                      │  crops   │──< crop_calendar
      │                      └──────────┘
      │
      ├──< refresh_tokens      ┌────────────────┐
      ├──< notifications ──────│ subscriptions  │
      ├──< notification_subs   └────────────────┘
      └──< audit_logs (actor)

  weather_snapshots  — standalone cache keyed by rounded lat/lon (no FK)
  otp_codes          — standalone, keyed by phone
```

---

## 3. Enums

```sql
user_role             AS ENUM ('farmer', 'expert', 'admin');
language_code         AS ENUM ('en', 'hi', 'mr', 'ta', 'te', 'bn', 'kn', 'gu', 'pa', 'or');
season                AS ENUM ('kharif', 'rabi', 'zaid', 'perennial');
irrigation_source     AS ENUM ('rainfed', 'canal', 'borewell', 'well', 'drip', 'sprinkler', 'tank');
soil_report_source    AS ENUM ('manual', 'shc_pdf', 'lab');
nutrient_status       AS ENUM ('very_low', 'low', 'medium', 'high', 'very_high');
pathogen_type         AS ENUM ('fungal', 'bacterial', 'viral', 'pest', 'nematode', 'nutrient_deficiency', 'abiotic');
treatment_kind        AS ENUM ('chemical', 'organic', 'cultural', 'preventive');
detection_status      AS ENUM ('completed', 'uncertain', 'rejected', 'failed');
review_status         AS ENUM ('none', 'pending_expert', 'confirmed', 'corrected', 'closed');
consultation_status   AS ENUM ('open', 'in_review', 'answered', 'closed', 'cancelled');
notification_channel  AS ENUM ('in_app', 'sms', 'push');
notification_status   AS ENUM ('pending', 'sent', 'failed', 'read');
ingestion_status      AS ENUM ('running', 'success', 'partial', 'failed');
```

Adding a value later is `ALTER TYPE ... ADD VALUE` (cannot be removed) — deliberate: enums are for stable, code-referenced sets. Free-text classifications use `VARCHAR` + a check constraint instead.

---

## 4. Tables

### 4.1 Identity

#### `users`

| column | type | null | notes |
|---|---|---|---|
| id | UUID | no | PK |
| phone | varchar(16) | no | UNIQUE, E.164 |
| email | citext | yes | UNIQUE when present |
| password_hash | varchar(255) | no | Argon2id |
| full_name | varchar(120) | yes | |
| role | user_role | no | default `farmer` |
| language | language_code | no | default `hi` |
| is_active | boolean | no | default true |
| phone_verified_at | timestamptz | yes | |
| last_login_at | timestamptz | yes | |
| created_at / updated_at | timestamptz | no | |
| deleted_at | timestamptz | yes | soft delete; phone unique is partial (`WHERE deleted_at IS NULL`) |

Indexes: `uq_users_phone (phone) WHERE deleted_at IS NULL`, `uq_users_email`, `idx_users_role`.

#### `refresh_tokens`

| column | type | notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK→users ON DELETE CASCADE | |
| token_hash | varchar(64) | UNIQUE — SHA-256 of the token, never the token |
| expires_at | timestamptz | |
| revoked_at | timestamptz | set on rotation/logout |
| replaced_by_id | UUID FK→refresh_tokens | rotation chain, for reuse-detection |
| user_agent | varchar(255) | |
| created_at | timestamptz | |

Indexes: `uq_refresh_tokens_token_hash`, `idx_refresh_tokens_user_id`, `idx_refresh_tokens_expires_at`.
Cleanup job deletes `expires_at < now() - 30 days`.

#### `otp_codes`

| column | type | notes |
|---|---|---|
| id | UUID PK | |
| phone | varchar(16) | |
| code_hash | varchar(64) | SHA-256(code + pepper); never store plaintext OTP |
| purpose | varchar(24) | `login`, `verify_phone`, `reset_password` |
| attempts | smallint | default 0, max 5 then locked |
| expires_at | timestamptz | 5-minute TTL |
| consumed_at | timestamptz | |
| created_at | timestamptz | |

Indexes: `idx_otp_codes_phone_purpose`. Used from Phase 11 (needs SMS); table exists from Phase 4 so the migration history stays linear.

---

### 4.2 Geography (reference data)

#### `agro_zones`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| code | varchar(12) | UNIQUE, e.g. `WESTERN_PLATEAU` |
| name | varchar(80) | e.g. "Western Plateau and Hills" |
| states | text[] | |
| notes | text | |

15 ICAR agro-climatic zones, seeded. Used by the crop rule layer.

#### `districts`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| state | varchar(60) | normalised display name |
| name | varchar(60) | normalised |
| slug | varchar(80) | UNIQUE (`state/name` slug) |
| agro_zone_id | UUID FK→agro_zones | nullable until mapped |
| latitude / longitude | numeric(9,6) | district HQ |
| created_at | timestamptz | |

Indexes: `uq_districts_slug`, `idx_districts_state`.

**Why this table exists:** AGMARKNET returns free-text district names with variants and typos. We normalise once into `districts` and keep a `market_aliases` mapping later if needed. Farms and markets both FK here, so "nearby mandis" and agro-zone lookups are joins, not string matching.

---

### 4.3 Farm context

#### `farms`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK→users CASCADE | |
| name | varchar(80) | e.g. "Wagh farm" |
| district_id | UUID FK→districts RESTRICT | |
| village | varchar(80) | |
| latitude / longitude | numeric(9,6) | NOT NULL — weather depends on it |
| area_acres | numeric(8,2) | |
| soil_type | varchar(24) | check constraint against allowed list |
| irrigation_source | irrigation_source | |
| primary_crop_id | UUID FK→crops SET NULL | |
| is_primary | boolean | default false; at most one primary per user |
| created_at / updated_at | timestamptz | |

Indexes: `idx_farms_user_id`, `uq_farms_user_primary (user_id) WHERE is_primary`.

#### `crops`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| slug | varchar(40) | UNIQUE, stable key used by rules and models |
| name_en / name_hi | varchar(60) | |
| scientific_name | varchar(80) | |
| category | varchar(24) | cereal / pulse / oilseed / vegetable / fruit / fibre / spice |
| season | season | |
| duration_days | smallint | |
| water_need | varchar(16) | low / medium / high |
| ideal_ph_min / ideal_ph_max | numeric(3,2) | used by soil analysis |
| n_p_k_target | jsonb | `{"n": 120, "p": 60, "k": 40}` kg/ha, crop-level default |
| agro_zones | text[] | zone codes where recommended |
| image_url | text | |
| is_active | boolean | |

**Critical mapping:** the ML model's 22 class labels map to `crops.slug` via `ml/crop_rec/labels.py`. If a label has no row, the seed fails loudly — we never ship a prediction with no catalogue entry.

#### `crop_calendar`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| crop_id | UUID FK→crops CASCADE | |
| agro_zone_id | UUID FK→agro_zones | nullable = all zones |
| activity | varchar(24) | sowing / fertilizer / irrigation / spray / weeding / harvest |
| month_start / month_end | smallint | 1–12; wrap allowed (11→2) |
| guidance | text | |
| source_url | text | |
| last_verified | date | |

Indexes: `idx_crop_calendar_crop_zone`. This is what makes PLAN's reminders real rather than generic.

---

### 4.4 PLAN

#### `soil_reports`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| farm_id | UUID FK→farms CASCADE | |
| user_id | UUID FK→users CASCADE | |
| source | soil_report_source | |
| tested_on | date | |
| nitrogen_kg_ha / phosphorus_kg_ha / potassium_kg_ha | numeric(7,2) | null-allowed individually: SHC cards often omit fields |
| ph | numeric(3,2) | CHECK 0–14 |
| organic_carbon_pct | numeric(4,2) | |
| ec_ds_m | numeric(5,2) | nullable |
| lab_name | varchar(120) | |
| document_key | text | object-storage key if a PDF was uploaded |
| notes | text | |
| created_at | timestamptz | |

Indexes: `idx_soil_reports_farm_id (farm_id, tested_on DESC)`.
CHECK: at least one of N/P/K/pH present (`num_nonnulls(...) >= 1`).

#### `soil_analyses`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| soil_report_id | UUID FK→soil_reports CASCADE | |
| crop_id | UUID FK→crops SET NULL | nullable: analysis without a target crop |
| statuses | jsonb | `{"n":"low","p":"medium","k":"high","ph":"slightly_acidic","oc":"low"}` |
| recommendations | jsonb | ordered list: `[{action, detail, priority, source}]` |
| ruleset_version | varchar(16) | so old analyses stay explainable after rule changes |
| created_at | timestamptz | |

Never recomputed in place: a new analysis row per run. History is the product.

#### `crop_recommendations`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| user_id / farm_id | UUID FK | farm CASCADE, user CASCADE |
| season | season | |
| input_features | jsonb | `{"n":90,"p":42,"k":43,"temperature":26.4,"humidity":80,"ph":6.5,"rainfall":202.9}` + `rainfall_source` |
| model_version | varchar(32) | |
| results | jsonb | ranked: `[{crop_slug, crop_name_en, probability, reasons[], agro_zone_ok, yield_range}]` |
| created_at | timestamptz | |

Indexes: `idx_crop_rec_farm_created (farm_id, created_at DESC)`.

#### `weather_snapshots`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| location_key | varchar(40) | `"lat:18.52,lon:73.86"` rounded to 0.01° (~1.1 km) |
| kind | varchar(16) | `current` / `forecast` |
| provider | varchar(24) | `openweathermap` / `openmeteo` |
| payload | jsonb | normalised, provider-independent shape |
| fetched_at | timestamptz | |
| expires_at | timestamptz | current: +10 min; forecast: +60 min |

Indexes: `uq_weather_snapshots_location_kind`, `idx_weather_snapshots_expires_at`.
This is our cache and our audit trail of what the user was actually shown. Phase 11 can move it to Redis; the table stays as the audit log.

---

### 4.5 PROTECT

#### `crop_diseases`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| crop_id | UUID FK→crops CASCADE | |
| slug | varchar(60) | UNIQUE — matches model label (`tomato__early_blight`) |
| name_en / name_hi | varchar(100) | |
| pathogen_type | pathogen_type | |
| symptoms | text | what the farmer sees, plain language |
| spread | text | how it spreads |
| severity_default | smallint | 1–5 |
| susceptible_stages | text[] | |
| image_url | text | |
| risk_humidity_min | smallint | null = not used by risk model |
| risk_temp_min / risk_temp_max | smallint | |
| is_active | boolean | |

**Seed constraint:** every label in the shipped model's `labels.json` must have a row here. A CI test enforces it (`tests/unit/test_reference_integrity.py`) — a prediction that renders as a raw slug is a product failure.

#### `disease_treatments`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| disease_id | UUID FK→crop_diseases CASCADE | |
| kind | treatment_kind | |
| title / description | varchar(120) / text | |
| dosage | varchar(160) | e.g. "2 g/L water, 200 L/acre" |
| safety_notes | text | PPE, pre-harvest interval |
| source_url | text | NOT NULL — every chemical recommendation is traceable |
| last_verified | date | NOT NULL |
| display_order | smallint | |

Curated by an agronomist, not generated. `source_url` NOT NULL is a deliberate schema-level guard: unverifiable advice cannot be inserted.

#### `disease_detections`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK→users CASCADE | |
| farm_id | UUID FK→farms SET NULL | |
| crop_id | UUID FK→crops SET NULL | |
| image_key | text | storage key, NOT NULL |
| image_sha256 | varchar(64) | dedupe + integrity |
| image_width / image_height | integer | |
| predicted_disease_id | UUID FK→crop_diseases SET NULL | top-1; null when rejected/uncertain |
| top_k | jsonb | `[{"slug":"tomato__early_blight","name":"Early blight","confidence":0.71}, …]` |
| max_confidence | numeric(5,4) | CHECK 0–1 |
| model_name / model_version | varchar(40) / varchar(32) | both NOT NULL |
| status | detection_status | |
| review_status | review_status | default `none` |
| expert_id | UUID FK→users SET NULL | |
| expert_note | text | |
| reviewed_at | timestamptz | |
| latency_ms | integer | |
| created_at | timestamptz | |

Indexes: `idx_detections_user_created (user_id, created_at DESC)`, `idx_detections_review (review_status) WHERE review_status = 'pending_expert'`, `idx_detections_farm_crop (farm_id, crop_id)` (disease history/risk), `uq_detections_image_sha_user (user_id, image_sha256)` — optional dedupe signal.

#### `consultations`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| detection_id | UUID FK→disease_detections CASCADE | nullable: free-form question |
| farmer_id | UUID FK→users CASCADE | |
| expert_id | UUID FK→users SET NULL | |
| status | consultation_status | |
| question | text | |
| answer | text | |
| voice_note_key | text | Phase 10 |
| created_at / answered_at / closed_at | timestamptz | |

Indexes: `idx_consultations_status (status, created_at)`, `idx_consultations_expert (expert_id) WHERE status IN ('open','in_review')`.

---

### 4.6 SELL

#### `commodities`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| slug | varchar(60) | UNIQUE |
| name_en / name_hi | varchar(80) | |
| category | varchar(24) | |
| default_unit | varchar(12) | `quintal` |
| aliases | text[] | AGMARKNET spelling variants, used by the normaliser |
| image_url | text | |

#### `markets`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| district_id | UUID FK→districts RESTRICT | |
| name | varchar(120) | as in AGMARKNET |
| slug | varchar(160) | UNIQUE (`state/district/market`) |
| latitude / longitude | numeric(9,6) | nullable; backfilled by geocoding admin action |
| is_active | boolean | |

Indexes: `uq_markets_slug`, `idx_markets_district`.

#### `mandi_prices`
| column | type | notes |
|---|---|---|
| id | bigserial PK | high-volume table; integer PK is cheaper than UUID here |
| market_id | UUID FK→markets CASCADE | |
| commodity_id | UUID FK→commodities CASCADE | |
| variety | varchar(80) | NOT NULL default `'Other'` |
| grade | varchar(20) | NOT NULL default `'FAQ'` |
| arrival_date | date | NOT NULL — the date the price refers to |
| min_price / max_price / modal_price | numeric(10,2) | CHECK `min_price <= modal_price <= max_price` where all present |
| unit | varchar(12) | `quintal` |
| source | varchar(24) | `agmarknet` |
| ingested_at | timestamptz | when *we* fetched it |

Indexes:
- `uq_mandi_prices_key (market_id, commodity_id, variety, grade, arrival_date)` — idempotent upserts
- `idx_mandi_prices_commodity_date (commodity_id, arrival_date DESC)` — price list + trends
- `idx_mandi_prices_market_date (market_id, arrival_date DESC)` — market page

**Honesty enforced by schema:** `arrival_date` is separate from `ingested_at`, and both are returned by the API. The UI must show `arrival_date`. This is data about a specific day, not "today's price".

#### `price_ingestion_runs`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| source | varchar(24) | |
| started_at / finished_at | timestamptz | |
| status | ingestion_status | |
| target_date | date | the arrival_date this run targeted |
| pages_fetched | integer | |
| rows_received / rows_upserted / rows_skipped | integer | |
| error_message | text | |
| created_at | timestamptz | |

Indexes: `idx_ingestion_started (started_at DESC)`. Surfaced in the admin panel — silent ingestion failure is the most likely way SELL quietly breaks.

#### `msp_rates`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| commodity_id | UUID FK→commodities RESTRICT | |
| season | season | |
| marketing_year | varchar(9) | e.g. `2026-27` |
| price_per_quintal | numeric(10,2) | |
| source_url | text | NOT NULL |
| published_on | date | NOT NULL |
| last_verified | date | NOT NULL |

UNIQUE `(commodity_id, season, marketing_year)`. Rows carry their own date, so an out-of-date table is visibly out-of-date rather than silently wrong.

---

### 4.7 Notifications & audit

#### `notifications`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK→users CASCADE | |
| channel | notification_channel | |
| category | varchar(32) | `weather_alert`, `disease_risk`, `price_alert`, `system`, `expert_reply` |
| title / body | varchar(140) / text | |
| payload | jsonb | deep-link target, e.g. `{"route":"/sell/prices","params":{...}}` |
| status | notification_status | |
| dedupe_key | varchar(120) | UNIQUE per user, e.g. `weather:rain:2026-11-24:farm:<id>` |
| scheduled_for | timestamptz | |
| sent_at / read_at | timestamptz | |
| provider_message_id | varchar(80) | SMS provider reference |
| created_at | timestamptz | |

Indexes: `idx_notifications_user (user_id, created_at DESC)`, `idx_notifications_pending (status, scheduled_for) WHERE status = 'pending'`, `uq_notifications_dedupe (user_id, dedupe_key)`.

#### `notification_subscriptions`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK→users CASCADE | |
| category | varchar(32) | |
| farm_id | UUID FK→farms CASCADE | nullable |
| channel | notification_channel | |
| enabled | boolean | |
| quiet_hours | jsonb | default `{"from":"21:00","to":"07:00"}` — TRAI requires this for SMS |

UNIQUE `(user_id, category, farm_id, channel)`.

#### `audit_logs`
| column | type | notes |
|---|---|---|
| id | bigserial PK | |
| actor_id | UUID FK→users SET NULL | |
| action | varchar(48) | `detection.review`, `user.role_change`, `reference.update` |
| entity | varchar(48) | table name |
| entity_id | UUID | |
| before / after | jsonb | |
| ip | inet | |
| created_at | timestamptz | |

Append-only. Indexes: `idx_audit_entity (entity, entity_id)`, `idx_audit_actor_created (actor_id, created_at DESC)`.

---

## 5. Cascade & deletion rules

| Relationship | Rule | Why |
|---|---|---|
| user → farms, soil_reports, detections, recommendations, notifications, consultations | `CASCADE` | account deletion must fully erase personal data (DPDP-friendly) |
| farm → soil_reports, recommendations, crop_recommendations | `CASCADE` | farm-scoped data is meaningless without the farm |
| farm → disease_detections | `SET NULL` | a detection is evidence worth keeping even if the farm record is removed |
| crop → crop_diseases, crop_calendar | `CASCADE` | reference data |
| crop_diseases → treatments | `CASCADE` | reference data |
| district → farms | `RESTRICT` | cannot orphan a farm's geography; admins must merge, not delete |
| market → mandi_prices | `CASCADE` | price history follows the market |
| users (hard delete) | blocked while `consultations` are open | prevents abandoning a farmer mid-question; route to account deactivation first |

`users` uses soft delete; a Phase 11 job hard-deletes after 30 days, and before that the account is anonymised (`full_name=NULL`, `phone` replaced with a tombstone value) so unique constraints free up.

---

## 6. Seed data plan

Seed lives in `backend/app/db/seed/` as versioned JSON, applied by an idempotent `python -m app.jobs.seed` that upserts on `slug`.

| Data | Rows | Source | Phase |
|---|---|---|---|
| agro_zones | 15 | ICAR agro-climatic zones | 4 |
| districts | ~780 (all India, or one state first) | LGD district directory | 4 |
| crops | ~25 (the 22 model classes + staples) | package-of-practices | 4 |
| crop_diseases | 26–30 | PlantVillage classes + field-relevant extras | 4 (metadata), 8 (labels finalised) |
| disease_treatments | 60–90 | ICAR/state PoP, each with `source_url` | 4 |
| commodities | ~40 top mandi commodities | AGMARKNET naming | 4 |
| markets | top 3–5 states (~1,200) | AGMARKNET market list | 9 (from ingested data) |
| msp_rates | ~25 × 2 seasons | CACP published tables | 9 |
| crop_calendar | ~120 | state PoP | 7 |

Rule: every row with agronomic or price content carries `source_url` + `last_verified`. Rows lacking a source are rejected at seed time — the seed loader validates this.

---

## 7. Volumes & growth (sizing the MVP)

| Table | MVP estimate | Growth |
|---|---|---|
| users | 100 demo / 10k realistic | linear |
| disease_detections | 1k | +~2k/month; **largest by row count**, ~200 KB/image in R2 not in PG |
| mandi_prices | **~4–5 million** (1,200 markets × 40 commodities × 100 days) | +40k/day. This is the volume driver |
| weather_snapshots | ~5k | TTL-pruned daily |

At ~5M price rows Postgres is entirely comfortable (< 1 GB). **No partitioning in the MVP**; when the table passes ~50M rows, switch to monthly `RANGE` partitions on `arrival_date`. Documented here so the decision isn't a surprise later.

Retention: `weather_snapshots` pruned after 7 days; `refresh_tokens` after expiry+30d; `mandi_prices` kept forever (it's the product's own price history).

---

## 8. Migration strategy

1. `alembic revision --autogenerate -m "..."` then **hand-review every generated migration** — autogenerate misses enum changes, partial indexes and check constraints.
2. One logical change per migration, named `NNNN_verb_noun` (e.g. `0003_add_mandi_price_unique_key`).
3. Every migration must be **reversible**: CI runs `alembic upgrade head` → `alembic downgrade base` → `upgrade head` on a throwaway database. A migration that cannot downgrade fails CI.
4. No data manipulation in schema migrations. Backfills are separate jobs (`app/jobs/backfill_*`) so they can be re-run.
5. Phase 4 exit criterion is exactly this loop, green.

---

## 9. Queries that define the design (sanity check)

If these are awkward, the schema is wrong. All should be single queries with no N+1:

```sql
-- compare one commodity across nearby mandis, latest day each reported
SELECT m.name, p.arrival_date, p.modal_price, p.min_price, p.max_price
FROM mandi_prices p JOIN markets m ON m.id = p.market_id
WHERE p.commodity_id = :commodity
  AND m.district_id IN (:districts)
  AND p.arrival_date = (SELECT max(arrival_date) FROM mandi_prices
                        WHERE market_id = p.market_id AND commodity_id = p.commodity_id);

-- price trend for one commodity in one state, last 90 days
SELECT arrival_date, avg(modal_price) AS avg_modal, count(*) AS markets
FROM mandi_prices p JOIN markets m ON m.id = p.market_id
WHERE p.commodity_id = :commodity AND m.district_id = ANY(:district_ids)
  AND p.arrival_date >= current_date - 90
GROUP BY arrival_date ORDER BY arrival_date;

-- disease risk for a farm's crop: recent humid forecast + diseases of that crop
SELECT d.name_en, d.symptoms FROM crop_diseases d
WHERE d.crop_id = :crop AND d.is_active
  AND d.risk_humidity_min IS NOT NULL;   -- filtered against forecast in Python

-- expert queue, oldest first
SELECT c.* FROM consultations c
WHERE c.status = 'open' ORDER BY c.created_at LIMIT 20;
```

---

## 10. Open items (resolved before Phase 4 ends)

1. **Districts scope:** all ~780 India districts, or one state to start? Default: seed full India (it's static reference data, ~1 MB) so AGMARKNET rows never fail to map.
2. **Model label ↔ crop mapping:** the 22 crop labels are `rice, maize, chickpea, kidneybeans, pigeonpeas, mothbeans, mungbean, blackgram, lentil, pomegranate, banana, mango, grapes, watermelon, muskmelon, apple, orange, papaya, coconut, cotton, jute, coffee`. Several are not "plantable per acre" in Maharashtra (apple, coffee) — the rule layer's zone filter must suppress them rather than the UI showing nonsense.
3. **Language codes:** ship `en` + `hi` in the schema but only those two translated; the rest of the enum exists so no migration is needed when they're added.
4. **`variety`/`grade` normalisation:** AGMARKNET uses many values ("Other", "Local", "FAQ", "Medium"). Phase 9 must decide whether the UI shows a single blended row or per-variety rows. **Default: per-variety rows, with a deliberate `Other` aggregate row clearly labelled** — blending different varieties into one "price" would be misleading.

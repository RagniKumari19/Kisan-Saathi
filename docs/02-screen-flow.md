# Phase 2 — Screen Flow & UX Specification

**Platform:** React Native + Expo (mobile, primary) · React + Vite (admin, Phase 11)
**Audience constraint:** users may be first-time smartphone users, reading fluently in one language only, often on a shared/low-end Android device with patchy 3G.
**Status:** Contract for Phase 6 (shell) and Phases 7–11 (modules).

---

## 1. Navigation map

Bottom tab bar with **5 tabs, always visible, always labelled** (icon + word, never icon-only). Depth is capped at 3 taps to any action.

```
                        ┌────────────────────┐
                        │  S0 Splash/Boot    │
                        └─────────┬──────────┘
                                  │ token? ──no──► ┌──────────────────┐
                                  │ yes           │ S1 Language      │
                                  ▼               └────────┬─────────┘
                        ┌────────────────────┐              ▼
                        │  T1 Home           │      ┌──────────────────┐
                        │  (dashboard)       │◄─────┤ S2 Login/Register│
                        └──┬───┬───┬───┬─────┘      └────────┬─────────┘
                           │   │   │   │                     │ new user
      ┌────────────────────┘   │   │   └──────────┐           ▼
      ▼                        ▼   ▼              ▼   ┌──────────────────┐
┌───────────┐          ┌──────────────┐   ┌────────────┐│ S3 Farm setup    │
│ T2 PLAN   │          │ T3 PROTECT   │   │ T4 SELL    ││ (district, GPS,  │
└──┬──┬──┬──┘          └──┬──┬──┬─────┘   └──┬──┬──┬───┘│  area, crop)     │
   │  │  │                │  │  │            │  │  │    └────────┬─────────┘
   │  │  └─► P3 Crop rec  │  │  └─► R3 History│  │  └─► M3 Trends   │
   │  └────► P2 Weather   │  └────► R2 Result  │  └────► M2 Compare  │
   └───────► P1 Soil      └───────► R1 Capture └───────► M1 Prices   │
                           │                                        │
                           └─► R4 Library (reference)               │
                                                                    ▼
                                          ┌──────────┐    ┌──────────────────┐
                                          │ T5 Profile│───►│ Notifications    │
                                          └────┬─────┘    │ Expert / Consult │
                                               │          │ Language, Logout │
                                               └──────────┘
```

`T2/T3/T4` are **hub screens**, not feature screens: each shows 2–4 large cards (e.g. PLAN → "Check my soil", "Weather", "Which crop?") so a farmer never has to guess where a capability lives.

---

## 2. Screen inventory

| # | Route | Screen | APIs | Phase |
|---|---|---|---|---|
| S0 | `/` | Splash / session restore | — | 6 |
| S1 | `/language` | Language selection | — | 6 |
| S2 | `/login`, `/register` | Login / Register | `POST /auth/login`, `/auth/register` | 6 |
| S3 | `/onboarding` | Farm setup wizard (3 steps) | `POST /users/me/farms`, `GET /crops`, `/meta` | 6 |
| T1 | `/(tabs)/index` | Home dashboard | `/weather/current`, `/disease/risk-alerts`, `/markets/prices`, `/meta` | 6/7 |
| T2 | `/(tabs)/plan` | PLAN hub | — | 7 |
| T3 | `/(tabs)/protect` | PROTECT hub | `/disease/library`, `/disease/risk-alerts` | 8 |
| T4 | `/(tabs)/sell` | SELL hub | `/markets/prices`, `/markets/msp` | 9 |
| T5 | `/(tabs)/profile` | Profile & settings | `/users/me`, `/notifications/subscriptions` | 6 |
| P1 | `/plan/soil` | Soil report entry | `POST /soil/analyze` | 7 |
| P2 | `/plan/soil/result/[id]` | Soil analysis result | `GET /soil/reports/{id}` | 7 |
| P2b | `/plan/weather` | Weather & advisories | `/weather/current`, `/forecast`, `/advisories` | 7 |
| P3 | `/plan/recommend` | Crop recommendation | `POST /crops/recommend` | 7 |
| P3b | `/plan/recommend/[id]` | Recommendation detail | `GET /crops/recommendations/{id}` | 7 |
| R1 | `/protect/capture` | Capture / upload leaf | `POST /disease/detect` | 8 |
| R2 | `/protect/result/[id]` | Detection result | `GET /disease/detections/{id}` | 8 |
| R3 | `/protect/history` | Past detections | `GET /disease/detections` | 8 |
| R4 | `/protect/library` | Disease library | `GET /disease/library` | 8 |
| M1 | `/sell/prices` | Mandi prices | `GET /markets/prices` | 9 |
| M2 | `/sell/compare` | Compare nearby mandis | `GET /markets/compare` | 9 |
| M3 | `/sell/trends` | Price trend chart | `GET /markets/trends` | 9 |
| M4 | `/sell/msp` | MSP reference | `GET /markets/msp` | 9 |
| X1 | `/notifications` | Notification list | `GET /notifications` | 11 |
| X2 | `/expert/[consultationId]` | Expert consultation thread | `/consultations` (Phase 11 contract) | 11 |
| X3 | `/voice` | Voice assistant (modal) | `POST /voice/query` | 10 |

25 routes = 16 farmer-facing screens + 5 tab/hubs + 4 shared/detail screens. **Phase 6 ships S0–S3, T1, T5** — enough for a real login and a real dashboard.

---

## 3. Screen specifications

Format: purpose · primary elements · states that must exist. Every screen must implement **loading, empty, error, stale-data and offline** — the four states most demos skip and most users actually see.

### S1 Language

Purpose: pick a language before any text appears.
- 2-column grid of large tiles, each with the language name **in its own script** (हिंदी, मराठी, English…) plus the English name underneath — a farmer who cannot read English must not need it to find their language.
- Selection applies immediately to the whole app (i18n `changeLanguage`) and persists.
- Only languages with complete translation files are shown. Half-translated Hindi appears here as English fallback, which looks broken; we gate the list on coverage ≥ 95%.

### S2 Login / Register

- Fields: phone (numeric keypad, `+91` prefix fixed and visible), password (with show/hide), full name (register only).
- "Have a soil card?" is **not** asked here — onboarding stays 3 steps, no more.
- Big primary button, full width, 56 px tall. Secondary link: "Create account" / "I already have an account".
- Errors inline under the field, in the chosen language, with the server's `error.code` mapped to a human sentence.
- No social login, no OTP button until Phase 11 (a disabled button with "coming soon" is worse than absence).

### S3 Farm setup (wizard)

Three steps, one question-group each, progress shown as "1 of 3":
1. **Where is your farm?** — state → district picker (searchable), then "Use my location" button (`expo-location`) with a manual lat/lon fallback. Village text field optional.
2. **How big and what soil?** — area in acres with a stepper (not a bare text field), soil type as 5 illustrated choices (black, red, alluvial, sandy, loamy) with a one-line description each.
3. **What do you grow?** — crop picker from `GET /crops`, filterable by district agro-zone; "skip for now" allowed.
- Saving sets the farm primary and lands on T1. Failure keeps the entered data (no losing a 3-step form to one 500).

### T1 Home dashboard

One scroll, ordered by urgency, not by module:
1. **Weather strip** — today's temp range, rain chance, one-line advisory if any (worst severity only).
2. **Alert cards** — disease risk for the current crop, price jump/drop for the current crop, expert reply. Max 3, each tappable to its detail.
3. **Three big module tiles** — PLAN / PROTECT / SELL, each with a one-line "what this does" subtitle for first-time users.
4. **Recent activity** — last detection thumbnail + last price check.
- Pull-to-refresh; skeleton loaders (not spinners) for the weather and alert areas.
- If no farm exists (user skipped), show a single prominent "Set up your farm" card instead of hiding sections.

### P1 Soil entry

- Grouped fields, one group per card: **Nitrogen, Phosphorus, Potassium** (kg/ha), **pH**, **Organic carbon (%)**, **EC** (optional).
- Each field has a "?" that opens a one-paragraph explanation plus "Where do I find this?" → shows how to read a Soil Health Card (image + text; this is reference content, not AI).
- Only pH and one nutrient are required — partial cards are common and the API handles nulls. The UI says "Fill what you have; we'll tell you what's missing" rather than blocking.
- Numeric keypads, inline range validation with the plausible range shown ("pH is usually between 4 and 10").
- Result (P2) is a separate route so it can be revisited from history.

### P2 Soil result

- Traffic-light status row per nutrient (colour **plus** a word — never colour alone).
- Recommendations as numbered cards, each with the source link in a collapsed "Source" row.
- Persistent disclaimer at the bottom: guidance vs. prescription.
- Actions: "Save" (implicit), "Check weather", "Which crop should I plant?" → cross-links into the module.

### P2b Weather

- Header: location name + "as of HH:MM".
- 5-day list: date, icon, min–max, rain mm, one-word condition. Tap a day → hourly/3-hourly detail sheet.
- Advisories section: severity icon + title + one line, tap to expand the full rule text and validity window.
- Footer note: "Advisories are calculated by this app from forecast data, not official warnings." (Api `disclaimer`)
- Stale data → amber bar: "Showing weather from 2 hours ago."

### P3 Crop recommendation

- Inputs are pre-filled from the saved farm + latest soil report + current weather; the farmer sees a summary ("Using your soil test from 10 Nov") with an "Edit" affordance. **No re-typing of 7 numbers.**
- Season selector: 3 large buttons (Kharif / Rabi / Zaid) with month ranges.
- Results: ranked cards, #1 visually emphasised but not labelled "best".
  - crop name in the farmer's language + English, probability band as a word ("strong match" / "possible"), 2–3 reason bullets.
  - "Why not <crop I grow>?" expandable → renders `suppressed` reasons.
  - No "expected yield" number unless the API returns a non-null `yield_range`.
- CTA: "Ask an expert" and "See market price for this crop".

### R1 Capture

- Camera preview with a **leaf outline overlay** and a one-line instruction: "One leaf, filling the box, in daylight."
- Two buttons: "Take photo" (primary, huge) and "Choose from gallery" (secondary).
- After capture: crop/rotate preview, then "Use this photo" / "Retake". Compression happens here, before upload, so the user sees the wait once.
- Upload state: determinate progress, "Checking your leaf…" with an estimated 5 s; cancellable.
- Client pre-checks: min resolution, warn on very dark images ("This photo looks dark — retake for a better result?").
- On `NO_LEAF_DETECTED`: stay on this screen with specific guidance, don't navigate to an empty result.

### R2 Detection result

Ordered by what the farmer needs, not by what the model produces:

1. **Verdict block** — disease name in their language, confidence as a word + percentage, severity dots, and the disclaimer immediately below (never at the bottom).
2. **Top-3 alternatives** — collapsed by default; labelled "Other possibilities".
3. **What to do** — treatments grouped: Cultural / Organic / Chemical (chemical last, with dosage + safety notes + pre-harvest interval).
4. **Actions** — "Send to expert" (primary when `status=uncertain`), "See library", "Take another photo".
5. **Metadata** — model version, timestamp, "how we got this" collapsible.

`status=uncertain` renders as a **distinct screen state**: no `predicted`, no treatments, an explicit "we're not sure" message and two paths (retake / expert). Rendering chemical advice here would be a safety bug.

### R3 History

- Grouped by month, thumbnail + crop + verdict + date, swipe (and a visible menu button) for delete.
- Empty state: "No checks yet — photograph a leaf to start."
- Filter chip by crop when the user has multiple farms/crops.

### R4 Library

- Search + crop filter, alphabetic list; detail shows symptoms, spread, favourable conditions, prevention, treatments.
- Every entry shows `last_verified` — this is reference content maintained by admins, and the date makes that visible.
- Reachable without login (reference content), but no treatment dosage is shown to unauthenticated users? **No — dosage is reference data, not personalised; it stays available.** Simpler and honest either way; documented so it isn't re-debated.

### M1 Prices

- Commodity selector (searchable, with the farmer's current crop pinned at top), district defaulting to the farm's district.
- Row: mandi name, modal price in ₹/quintal large, min–max underneath, **date** on every row, variety/grade as a small chip.
- Sort: nearest / highest price / latest date.
- Header shows data date and a freshness badge. No live-ticker pretence.
- Empty: "No arrivals reported for this crop in your district on 21 Nov." + button "Show nearby districts" (uses `meta.nearest_with_data`).

### M2 Compare

- Horizontal bar chart: one bar per mandi, modal price, distance label; the farm's current mandi highlighted.
- Table below with `net_after_transport` and an info tap explaining the estimate (rate + formula).
- Explicit note: "Transport cost is an estimate, not a quote from a transporter."

### M3 Trends

- Line chart, 7/30/90-day toggle, daily average modal price, with a shaded band for min–max across markets.
- Gap handling: missing days are gaps, **not** interpolated lines. A broken line is honest; a smoothly interpolated one is a lie.
- Caption: "Average of modal prices reported by mandis in <district>. Not every mandi reports every day."

### M4 MSP

- Table by season with `marketing_year`, price, and "published on <date>" + source link.
- Banner if the table is older than the current marketing year: "This table may be out of date."

### T5 Profile

- Name, phone (masked), language switcher, farm list (add/edit/delete), notification preferences (per category, with quiet-hours note), logout, app version, and a "Data sources" screen listing every external provider with its last successful update.

---

## 4. Critical journeys

### 4.1 First run (target: under 90 seconds to a useful dashboard)

```
S0 boot → S1 language → S2 register (phone, password, name) → S3 farm (district, GPS, acres, soil, crop)
→ T1 dashboard with real weather for that district
```
Time budget: 3 network calls, 3 screens, 2 required text inputs (phone, password), 1 number (acres). Anything longer loses users.

### 4.2 Disease detection (target: 4 taps, < 20 s)

```
T1 alert or T3 → R1 capture → shutter → "Use this photo" → upload → R2 result → [escalate] → X2
```
Failure paths that must be designed: too dark, not a leaf, offline (queue the photo? **no** — MVP shows "you're offline, try again when connected" and keeps the image locally), model unavailable (`503` → screen explains, offers library + expert instead of a dead end).

### 4.3 Price check (target: 2 taps from dashboard)

```
T1 "Sell" tile → M1 (pre-selected: farm's crop, farm's district) → row tap → M2 compare
```
The default selection is the whole feature: zero-configuration for the common case.

### 4.4 Expert escalation

```
R2 "Send to expert" → optional note + voice note (P10) → X2 thread, status "Waiting for expert"
→ push/in-app notification on reply → X2 shows answer + "Was this helpful?"
```
Expert side is admin-web (Phase 11): queue → detection image + model output side by side → confirm/correct → reply.

---

## 5. Design rules (non-negotiable)

| Rule | Value |
|---|---|
| Base font size | 18 px body, 22 px headings, 28 px numbers that matter (price, temperature) |
| Tap targets | ≥ 56 × 56 px, 12 px minimum spacing |
| Contrast | WCAG AA (4.5:1); test with the actual palette, including the "warning amber on cream" case that usually fails |
| Colour | Never the only signal — pair with icon + word (a red/green-only result is unreadable to colour-blind users and in sunlight) |
| Text length | Labels ≤ 3 words; sentences ≤ 12 words; no agronomic jargon without a plain-language gloss |
| Numbers | Indian digit grouping (₹1,750 / ₹12,500) and local numerals where the language expects them |
| Icons | Always with labels; no bottom-tab icon-only mode |
| Forms | One question group per screen section, autosave drafts locally, never a modal keyboard covering the field |
| Destructive actions | Confirm dialog with the verb ("Delete this photo?"), never a bare trash icon |
| Loading | Skeletons for content, progress for uploads, no full-screen spinners over 400 ms |
| Error copy | Say what happened + what to do next, in the user's language, no codes shown to farmers (codes stay in logs) |

**Accessibility:** dynamic type respected up to 200% without clipping (test with system font at max), screen-reader labels on all controls (`accessibilityLabel` in the current language), focus order matching visual order, reduce-motion respected for the chart animations.

**Low-end device budget:** initial JS bundle target < 3 MB, images lazy-loaded and cached, chart library must render without a WebView (`react-native-svg`), app usable on Android 8 / 2 GB RAM.

---

## 6. i18n strategy

- All strings in `mobile/src/i18n/{lang}.json`, keyed by domain (`home.weather.title`). No inline literals — a CI check fails the build on a string literal in a `<Text>` that isn't a number or a proper noun.
- Dates/numbers via `Intl` with the locale; units stay metric (acre, quintal, °C) because those are what farmers and mandis use — we do not convert to hectares silently.
- Server-provided dynamic text (`summary_en`, `message_en`, rule titles) is returned **pre-translated where it is static content** (reference data has `name_hi`, advisory rules ship `title_hi`), not machine-translated at request time. Machine translation is reserved for user-generated text and is always labelled ("auto-translated") — a mistranslated pesticide dosage is a safety incident.
- Fallback chain: `hi` → `en` → key. Missing keys are visible in dev via a red badge (`__MISSING__`), caught by the coverage check before release.
- Pluralisation via ICU message format; Hindi plural rules differ from English and hand-concatenated strings break.
- Layout tolerance: Hindi/Marathi run ~15–30% longer than English in the same string — every button is tested at 130% width, and no text is hard-truncated with ellipsis on a primary action.

---

## 7. Analytics events (privacy-respecting, Phase 12)

`screen_view`, `detection_started/completed/failed(reason)`, `recommendation_viewed`, `price_viewed`, `advisor_shown(rule_id)`, `expert_escalated`, `language_changed`. No phone numbers, no image content, no precise coordinates in analytics (district-level only). Every event carries `model_version` when AI output is shown — so we can later ask "did confidence predict usefulness?".

---

## 8. Admin web (Phase 11, scoped)

Four pages, no more: **Detections queue** (review/correct), **Reference data** (crops, diseases, treatments, MSP, calendar — with `source_url` + `last_verified` required), **Ingestion** (run history, manual trigger, error detail), **Stats**. Desktop-only, table-first, no design system beyond shadcn defaults. Admin is a tool for two people, not a product.

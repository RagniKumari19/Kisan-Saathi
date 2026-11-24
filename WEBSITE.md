# Farmer Assistance Platform — Website

Web app for the Farmer Assistance Platform, built with **React 18 + TypeScript + Vite**, styled with a tokenized navy/teal theme and served by the FastAPI backend (port 8000). Supports English and Hindi, light/dark/system theme, and mobile-responsive layout.

## Entry points

- Dev: `cd web && npm install && npm run dev` → `http://localhost:5173` (proxies `/api` and `/media` to `:8000`)
- Prod: `cd web && npm run build`, then restart the backend → `http://127.0.0.1:8000/` (serves `web/dist`, including SPA deep links)

## Authentication

- `/login`, `/register` — phone OTP (default) or password sign-in; no demo accounts.
- Protected app shell at `/app` with sidebar (desktop) and bottom tab bar (mobile).

## App routes

### Home
- `/app` — Dashboard: greeting, farm selector, weather/advisory, **Smart Crop Recommendations** (weather + soil summary, season selector, ranked crops with reasons, suppressed list, crop detail links), recent activity.

### Plan
- `/app/plan` — Plan hub
- `/app/plan/soil` — soil report entry and interpretation
- `/app/plan/weather` — weather and advisories
- `/app/plan/recommend` — crop recommendation
- `/app/plan/crops`, `/app/plan/crops/:slug` — crop library/detail

### Protect
- `/app/protect` — protect hub
- `/app/protect/capture` — leaf photo upload
- `/app/protect/history` — past checks
- `/app/protect/library`, `/app/protect/library/:slug` — disease library
- `/app/protect/:id` — detection result

### Sell
- `/app/sell` — sell hub
- `/app/sell/prices` — mandi prices
- `/app/sell/compare` — market comparison
- `/app/sell/trends` — price trends
- `/app/sell/msp` — MSP rates

### Account / Admin
- `/app/profile` — profile and farms
- `/app/farms/new`, `/app/farms/:id` — farm create/edit
- `/app/expert` — expert review queue (expert/admin)
- `/app/admin` — admin dashboard (admin)

## Key UI components

- `card`, `grid`, `tile`, `stat`, `alert`, `meter`, `pill`, `badge` — tokenized layout primitives
- `MockBadge` — labels demo vs. live data
- `Empty`, `Loading`, `ErrorNote` — state components
- `Icon`, `PageHead`, `Modal` — shared UI

## Data & services

- API client: `web/src/api.ts` (bearer auth, refresh-token handling)
- Auth/farm context: `web/src/session.tsx`
- i18n: `web/src/i18n.tsx` (en/hi)
- Theme: `web/src/theme.ts` (light/dark/system)
- All API keys stay on the backend; the web app never calls third-party services directly.

## Demo accounts

| Role | Phone | Password |
|---|---|---|
| Farmer | `+919876543210` | `farmer123` |
| Expert | `+919876543211` | `expert123` |
| Admin | `+919876543212` | `admin123` |

## Design principles

- No fake data in decision features; mock data is labelled with `provenance.is_mock`.
- “We don’t know” is a designed state (e.g. `uncertain` disease result has no treatments).
- Agronomic guidance is rules-based and sourced, not LLM-generated.
- Mobile-first responsive layout with accessible skip link, keyboard support, and ARIA labels.

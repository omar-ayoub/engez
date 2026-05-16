# Research: Phase 1 — Foundation

**Date**: 2026-05-15

## R1: JWT Token Strategy (Access + Refresh)

**Decision**: Dual-token system — short-lived access token (30 min) + long-lived refresh token (7 days). Refresh token stored in httpOnly cookie; access token in memory (Zustand).

**Rationale**: A single 24h token is too coarse. Short access tokens limit damage from token theft. The refresh token in an httpOnly cookie survives page reloads without XSS exposure. Silent refresh happens automatically before access token expiry. For offline scenarios, the client operates on cached data and re-authenticates on reconnect.

**Alternatives considered**:
- Single long-lived JWT (24h): Simple but high exposure window if stolen. Rejected.
- Session-based auth (server-side): Requires server round-trip on every request. Breaks offline-first. Rejected.

## R2: Biometric Re-Authentication via WebAuthn

**Decision**: Use the Web Authentication API (navigator.credentials) with platform authenticators (fingerprint/face). Store the WebAuthn credential ID server-side linked to the user. On token expiry + reconnect, the client prompts biometric challenge → server verifies → issues new token pair.

**Rationale**: Field workers wear gloves; biometric (thumbprint sensor area is usually exposed) is faster than typing email/password. WebAuthn is supported on Chrome Android 67+, Safari iOS 14+ — matching our PWA target.

**Alternatives considered**:
- PIN-based re-auth: Requires remembering another secret. Rejected.
- No re-auth (just re-login): Full email/password with gloves is slow. Rejected.

## R3: Login Rate Limiting Implementation

**Decision**: Track `failed_login_attempts` and `locked_until` columns on the User model. Increment on failure, reset on success. Lock account when attempts reach 5. Auto-unlock after 15 minutes (check `locked_until < now()`).

**Rationale**: Database-level tracking is simpler than Redis-based rate limiting for login specifically. It also survives backend restarts. Redis rate limiting is reserved for API-wide throttling in later phases.

**Alternatives considered**:
- Redis-based sliding window: Over-engineered for login; adds dependency for a simple counter. Better suited for API rate limiting. Rejected for login.
- IP-based rate limiting at Nginx: Doesn't protect against distributed attacks targeting a single account. Rejected as sole mechanism.

## R4: Expense Categories — Data Model

**Decision**: New `categories` table with `id`, `company_id`, `name`, `name_ar`, `sort_order`, `is_active`, timestamps. Expense.category_id FK references this table. CLI seed command creates default Egyptian categories per company.

**Rationale**: Predefined per-company categories give accountants consistent reporting dimensions. The `sort_order` field lets admins control display order. AI (in later phases) maps receipts to category IDs from this table, not free-text.

**Default seed categories** (Egyptian construction/logistics context):
- مواد بناء (Building Materials)
- نقل ومواصلات (Transportation)
- عمالة (Labor)
- طعام وشراب (Food & Beverage)
- معدات (Equipment)
- إيجار (Rent)
- مرافق (Utilities)
- متنوعة (Miscellaneous)

**Alternatives considered**:
- Global category enum: Inflexible across industries. Rejected.
- Free-text: Inconsistent data, harder to report. Rejected.
- Hybrid (predefined + "other"): "Other" becomes a dumping ground. Rejected.

## R5: Offline-First Client Architecture

**Decision**: Dexie.js for IndexedDB, vite-plugin-pwa with Workbox 7 for service worker. Three-tier caching:
1. **Precache** (install): App shell, fonts, locale JSON, static assets
2. **Runtime cache** (CacheFirst): Fonts, images
3. **Runtime cache** (NetworkFirst, 5s timeout): API responses

Sync queue: Dexie table `syncQueue` stores pending mutations. Background Sync API triggers replay on reconnect. Polling fallback (30s interval) for Safari/iOS.

**Rationale**: Dexie.js provides a clean Promise-based API over IndexedDB with schema versioning. Workbox handles service worker complexity. The three-tier strategy ensures the app shell loads instantly while API data stays fresh.

**Alternatives considered**:
- PouchDB + CouchDB: Full sync protocol is overkill; we only sync expense submissions upstream. Rejected.
- localForage: No schema versioning, no live queries. Rejected.

## R6: Arabic RTL with Tailwind CSS 4

**Decision**: Use Tailwind CSS 4 with `@tailwindcss/vite` plugin. Tailwind 4 natively supports logical properties via the `rtl:` variant and `*-inline-start`/`*-inline-end` utilities. shadcn/ui components with `rtl: true` in components.json auto-adapt.

**Rationale**: Tailwind 4 generates logical CSS properties by default when using utilities like `ms-4` (margin-inline-start) and `pe-2` (padding-inline-end). This eliminates the need for manual LTR/RTL switching. The `dir` attribute on `<html>` controls everything.

**Alternatives considered**:
- Manual CSS with logical properties: More verbose, harder to maintain. Rejected.
- rtlcss post-processing: Adds build complexity and can break custom styles. Rejected.

## R7: Docker Development Environment

**Decision**: Docker Compose with three services: `postgres` (16-alpine), `redis` (7-alpine), `api` (Python 3.13-slim with uv). Frontend runs natively via `pnpm dev` with Vite proxy to `localhost:8000`. No frontend container in dev (HMR performance on Windows is poor in Docker).

**Rationale**: Running the frontend natively avoids WSL2/Docker volume mount performance issues on Windows. The backend runs in Docker for PostgreSQL/Redis parity with production. `fastapi dev` in the API container enables hot reload.

**Alternatives considered**:
- Full Docker (including frontend): Poor HMR performance on Windows due to filesystem watchers over volume mounts. Rejected for dev.
- No Docker (native everything): Requires local PostgreSQL and Redis installation. Rejected for onboarding simplicity.

## R8: Database ID Strategy

**Decision**: UUID v4 as strings (`String(36)`) for all primary keys. Generated client-side for expenses (enables offline creation), server-side for other entities.

**Rationale**: UUIDs enable offline expense creation without server coordination. String representation is portable across PostgreSQL and IndexedDB. The 36-char overhead is acceptable for the expected data volumes.

**Alternatives considered**:
- Auto-increment integers: Cannot generate offline. Rejected for expenses.
- UUID as native PostgreSQL `uuid` type: Better storage but complicates Dexie.js interop (must store as string client-side anyway). Rejected for simplicity.
- ULID: Sortable by time, but adds a dependency. UUID v4 is sufficient. Rejected.

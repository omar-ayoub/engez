# ENGEZ - Field Expense PWA

## Project Overview

**ENGEZ** (إنجز) is an offline-first PWA for Egyptian enterprise field expense management.
Target: construction, events, freight companies. Arabic-first RTL, dark mode default.

## Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | React 19.2, TypeScript 6.0, Vite 8, Tailwind 4, shadcn/ui, Dexie 4.4, Zustand 5, react-hook-form 7, react-i18next 15 |
| Backend | Python 3.13, FastAPI 0.136, SQLAlchemy 2.0 async, Pydantic 2.13, uvicorn |
| Database | PostgreSQL 16 + asyncpg, Redis 7, IndexedDB (Dexie.js), Cloudflare R2 |
| AI | OpenAI gpt-4o-mini-transcribe (voice), gpt-4o (receipt OCR) |
| Testing | pytest + pytest-asyncio (backend), Playwright 1.60 (E2E), Vitest (unit - planned) |
| Package Mgmt | pnpm 9 (frontend), uv (backend) |

## Project Structure

```
backend/
  app/
    api/v1/          # FastAPI routers (auth, expenses, voice, receipts, vendors, etc.)
    core/            # config, database, deps (DI), security (JWT)
    models/          # SQLAlchemy models (Base uses UUID PKs, company_id tenant scope)
    schemas/         # Pydantic request/response schemas
    services/        # Business logic (AI, R2 storage, rate limiter, QR decode)
  tests/             # pytest-asyncio tests with SQLite mock (no PostgreSQL needed)
  alembic/           # DB migrations

frontend/
  src/
    features/capture/  # Feature module: expense capture (voice, receipt, manual, combined)
      components/      # VoiceRecordButton, ReceiptCamera, ExpenseForm, CategoryGrid, etc.
      hooks/           # useVoiceCapture, useReceiptCapture, useExpenseForm, useDraftProcessor
      pages/           # CapturePage, DraftReviewPage
      store.ts         # Zustand capture state
    components/ui/     # shadcn/ui components (RTL-ready)
    hooks/             # Shared hooks (useDirection, useOnlineStatus, useSyncStatus)
    lib/               # Core utilities (db.ts, sync.ts, auth.ts, i18n.ts, image-compress.ts)
    sw/                # Custom service worker (injectManifest strategy)
    locales/           # i18n JSON files (ar/, en/) - imported directly, NOT from public/
    pages/             # Top-level pages (Login, Home)
  e2e/                 # Playwright E2E tests
  public/              # Static assets only (no locale files)

specs/                 # Spec-Kit workflow artifacts per feature
  001-phase1-foundation/
  002-core-expense-capture/
    plan.md            # Current implementation plan (detailed architecture reference)
    spec.md            # Feature specification
    tasks.md           # Implementation tasks
```

## Commands

### Backend (run from `backend/`)
```bash
uv run pytest                      # Run all tests (25 tests, uses SQLite mock)
uv run pytest -x                   # Stop on first failure
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000  # Dev server
uv run ruff check .                # Lint
uv run ruff format .               # Format
uv run alembic upgrade head        # Run migrations (requires PostgreSQL)
```

### Frontend (run from `frontend/`)
```bash
pnpm dev                           # Vite dev server on :5173
pnpm build                         # TypeScript check + production build
pnpm lint                          # ESLint
pnpm test:e2e                      # Playwright tests (auto-starts backend + frontend)
pnpm test:e2e:ui                   # Playwright with UI mode
npx playwright install chromium    # Install browser (after @playwright/test upgrade)
```

### Full validation (from project root)
```bash
cd backend && uv run pytest && cd ../frontend && pnpm build && pnpm lint && pnpm test:e2e
```

## Architecture Conventions

### Multi-Tenancy
- Every DB record has `company_id` — enforced via `get_tenant_scope` dependency
- JWT contains `user_id`, `company_id`, `role`
- All queries MUST filter by company_id

### Offline-First
- All writes go to IndexedDB (Dexie.js) first, then sync to backend
- Service worker: injectManifest strategy with Background Sync
- Voice/receipt blobs use draft-hold workflow (AI processes when online, user confirms)
- `devOptions: { enabled: false }` in vite.config.ts (prevents dev SW errors in E2E)

### RTL / i18n
- Arabic-first, CSS logical properties (start/end, not left/right)
- i18n files in `src/locales/` (imported directly, NOT from `public/`)
- Namespace pattern: `common.json` + feature-specific (e.g., `capture.json`)
- `useDirection()` hook sets document dir attribute

### Authentication
- Login returns access_token (short-lived) + refresh_token (httpOnly cookie)
- `useAuthStore` (Zustand + localStorage persistence) tracks auth state
- `ProtectedRoute` / `PublicRoute` wrappers in App.tsx
- E2E tests inject localStorage to bypass real auth

### API Proxy
- Frontend Vite proxies `/api` to `http://localhost:8000`
- Backend routes mounted at `/api/v1/`

## Testing Patterns

### Backend (pytest-asyncio)
- Uses SQLite mock via aiosqlite (no PostgreSQL required for tests)
- `conftest.py` patches JSONB -> JSON and `now()` server defaults for SQLite compat
- Fixtures: `auth_client` (field worker), `admin_client` (admin role)
- AI services mocked via `unittest.mock.patch`
- Rate limiter mocked in auth_client fixture

### E2E (Playwright 1.60)
- Fixture pattern: `async ({}, use) => { await use(value) }` (required in Playwright 1.60+)
- Auth bypass: inject `auth-storage` key into localStorage before navigation
- Selectors: prefer `getByRole`, `getByText`, `getByPlaceholder`; use `.first()` for strict mode
- Language-agnostic assertions: `page.getByText("X").or(page.getByText("Y"))`
- `webServer` config auto-starts both backend (uvicorn) and frontend (vite)

## Known Platform Gotchas (Windows)

- **FastAPI CLI crashes** on Windows due to Rich emoji encoding (cp1252). Use `uvicorn` directly.
- **Vite 8 strict imports**: Cannot import from `public/` directory in JS/TS. Locale files live in `src/locales/`.
- **Playwright browser mismatch**: After upgrading `@playwright/test`, always run `npx playwright install chromium`.
- **Git line endings**: Repo uses LF. Ensure `core.autocrlf=input` in git config.

## Constitution Principles (must not violate)

1. **Offline-First** — All features must work without network
2. **Arabic-First RTL** — CSS logical properties, RTL layout default
3. **Multi-Tenant Isolation** — company_id on every record, no cross-tenant leaks
4. **Field-Worker UX** — 44px touch targets, <15s task completion, dark mode
5. **Spec-Driven Development** — Spec-Kit workflow before feature code
6. **Security by Default** — Signed URLs, rate limiting, JWT auth, input validation

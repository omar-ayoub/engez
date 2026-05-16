# Implementation Plan: Phase 1 — Foundation

**Branch**: `001-phase1-foundation` | **Date**: 2026-05-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-phase1-foundation/spec.md`

## Summary

Build the ENGEZ foundation layer: a full-stack PWA scaffold with Arabic-first RTL design system, offline-first client architecture (Dexie.js + service worker), JWT-based multi-tenant authentication with biometric re-login, a PostgreSQL schema for 7 entities (Company, User, Project, Category, Expense, CorrectionFeedback, VendorCache), and bilingual i18n. The backend is a FastAPI async service behind Docker Compose; the frontend is a React 19.2 PWA with Tailwind CSS 4 and shadcn/ui in RTL mode.

## Technical Context

**Language/Version**: Frontend: TypeScript 6.0 on React 19.2 | Backend: Python 3.13

**Primary Dependencies**:
- Frontend: Vite 8 (Rolldown), Tailwind CSS 4, shadcn/ui (RTL), Dexie.js 4.4, React Router 7, Zustand 5, react-i18next 15, React Hook Form 7, vite-plugin-pwa 0.21
- Backend: FastAPI 0.136, SQLAlchemy 2.0 (async), Pydantic 2.13, Alembic 1.14, python-jose, passlib[bcrypt], asyncpg

**Storage**: PostgreSQL 16 (primary), Redis 7 (rate limiting + cache), IndexedDB via Dexie.js (client-side offline)

**Testing**: Frontend: Vitest + Testing Library React | Backend: pytest + pytest-asyncio + httpx

**Target Platform**: PWA on modern browsers (Android 8+, iOS 14+), backend on Ubuntu 24.04 LTS VPS

**Project Type**: Web application (frontend PWA + backend API)

**Performance Goals**: Login → home screen in <3s, offline app load <2s, expense submission <15s from app open

**Constraints**: Offline-capable, RTL-first, 44px min touch targets, dark mode default, WCAG AA, multi-tenant isolation

**Scale/Scope**: Initial deployment for Egyptian enterprises; single region; dozens of companies, hundreds of users per company

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
| --------- | ------ | -------- |
| I. Offline-First Architecture | PASS | Dexie.js for IndexedDB writes before network; sync queue with Background Sync API + polling fallback for Safari/iOS; service worker precaches app shell, fonts, locale files; network failures never block expense submission |
| II. Arabic-First RTL | PASS | HTML `dir=rtl` default; Tailwind CSS 4 logical properties; IBM Plex Arabic primary font; LTR numeric amounts with `tabular-nums`; react-i18next with `ar`/`en` namespaces; shadcn/ui RTL mode |
| III. Multi-Tenant Data Isolation | PASS | `company_id` on every tenant-scoped model via `TenantMixin`; FastAPI dependency injects tenant scope from JWT; automated cross-tenant isolation tests. RLS deferred per constitution (SHOULD, not MUST) |
| IV. Field-Worker UX Priority | PASS | 44x44px touch targets; 15s critical path; <=3 taps navigation; dark mode default; WCAG AA contrast; no decorative illustrations |
| V. Spec-Driven Development | PASS | Following specify → clarify → plan → tasks → implement workflow |
| VI. Security by Default | PASS | JWT with bcrypt-hashed passwords; HTTPS in production; Docker non-root in production; secrets via env vars/.env; login rate limiting (5 attempts/15min lockout); biometric WebAuthn for re-login |

**Gate result: ALL PASS** — no violations, no complexity tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/001-phase1-foundation/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: technology decisions
├── data-model.md        # Phase 1: entity schemas
├── quickstart.md        # Phase 1: dev environment setup
├── contracts/           # Phase 1: API contracts
│   ├── auth.md          # Authentication endpoints
│   └── admin.md         # Admin management endpoints
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py                  # FastAPI application entry point
│   ├── core/
│   │   ├── config.py            # Pydantic settings (env vars)
│   │   ├── security.py          # JWT, bcrypt, WebAuthn helpers
│   │   ├── database.py          # Async SQLAlchemy engine + session
│   │   └── deps.py              # FastAPI dependencies (auth, tenant scope)
│   ├── models/
│   │   ├── base.py              # DeclarativeBase, TimestampMixin, TenantMixin
│   │   ├── company.py           # Company model
│   │   ├── user.py              # User model (with login_attempts, locked_until)
│   │   ├── project.py           # Project model
│   │   ├── category.py          # Category model (per-company)
│   │   ├── expense.py           # Expense model
│   │   ├── correction.py        # CorrectionFeedback model
│   │   └── vendor_cache.py      # VendorCache model
│   ├── schemas/
│   │   ├── auth.py              # Login request/response, token schemas
│   │   ├── user.py              # User CRUD schemas
│   │   ├── company.py           # Company CRUD schemas
│   │   ├── project.py           # Project CRUD schemas
│   │   └── category.py          # Category CRUD schemas
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py          # POST /login, POST /refresh, POST /webauthn/*
│   │       ├── users.py         # CRUD users (admin only)
│   │       ├── companies.py     # CRUD companies (admin only)
│   │       ├── projects.py      # CRUD projects (admin only)
│   │       └── categories.py    # CRUD categories (admin only)
│   └── services/
│       ├── auth_service.py      # Login logic, lockout, token refresh
│       └── seed.py              # CLI seed command for initial admin
├── alembic/
│   ├── env.py                   # Async Alembic config
│   └── versions/                # Migration files
├── tests/
│   ├── conftest.py              # Fixtures (async DB, test client, tenant factory)
│   ├── test_auth.py             # Auth endpoint tests
│   └── test_tenant_isolation.py # Cross-tenant query verification
├── pyproject.toml               # Dependencies (uv)
├── Dockerfile                   # Python 3.13-slim + uv
└── .env.example                 # Template for required env vars

frontend/
├── public/
│   ├── locales/
│   │   ├── ar/common.json       # Arabic translations
│   │   └── en/common.json       # English translations
│   ├── pwa-192x192.png          # PWA icons
│   └── pwa-512x512.png
├── src/
│   ├── main.tsx                 # App entry point
│   ├── App.tsx                  # Root component with providers
│   ├── index.css                # Tailwind + IBM Plex Arabic + theme tokens
│   ├── components/
│   │   └── ui/                  # shadcn/ui components (RTL mode)
│   ├── lib/
│   │   ├── db.ts                # Dexie.js offline database schema
│   │   ├── auth.ts              # Zustand auth store (persistent)
│   │   ├── i18n.ts              # react-i18next config (ar default)
│   │   ├── api.ts               # HTTP client with auth headers
│   │   └── sync.ts              # Sync queue manager
│   ├── pages/
│   │   ├── Login.tsx            # Login page (email/password + biometric)
│   │   └── Home.tsx             # Home screen (role-based)
│   └── hooks/
│       ├── useOnlineStatus.ts   # Network connectivity hook
│       └── useDirection.ts      # RTL/LTR direction hook
├── components.json              # shadcn/ui config (RTL enabled)
├── vite.config.ts               # Vite + PWA + Tailwind + proxy
├── tsconfig.json                # TypeScript strict config
└── package.json                 # Dependencies (pnpm)

docker-compose.yml               # PostgreSQL 16, Redis 7, API service
.env.example                     # Root env var template
```

**Structure Decision**: Web application layout with `backend/` and `frontend/` at repository root. Docker Compose orchestrates all services for local development. The frontend dev server proxies `/api` requests to the backend container at port 8000.

## Complexity Tracking

> No constitution violations detected. Table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | — | — |

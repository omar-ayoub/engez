<!--
  Sync Impact Report
  ==================
  Version change: N/A → 1.0.0 (initial ratification)
  Added principles:
    - I. Offline-First Architecture
    - II. Arabic-First RTL
    - III. Multi-Tenant Data Isolation
    - IV. Field-Worker UX Priority
    - V. Spec-Driven Development
    - VI. Security by Default
  Added sections:
    - Technology Stack Constraints
    - Development Workflow
    - Governance
  Removed sections: none
  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ compatible (Constitution Check section exists)
    - .specify/templates/spec-template.md ✅ compatible (no constitution-specific gates)
    - .specify/templates/tasks-template.md ✅ compatible (phase structure aligns)
  Follow-up TODOs: none
-->

# ENGEZ (إنجز) Constitution

## Core Principles

### I. Offline-First Architecture

Every user-facing feature MUST function without a network connection.
Offline capability is not a progressive enhancement — it is the default state.

- All data entry forms MUST write to IndexedDB (via Dexie.js) before
  attempting any network request.
- A sync queue MUST persist unsubmitted records and replay them
  automatically when connectivity is restored.
- Background Sync API is the primary sync mechanism; a polling fallback
  MUST exist for browsers that lack Background Sync support (Safari/iOS).
- The service worker MUST precache all app shell assets, fonts, and
  locale files so the app launches instantly on repeat visits.
- Network failures MUST NEVER cause data loss or block the user from
  completing an expense submission.

### II. Arabic-First RTL

Arabic (Egyptian dialect) is the default language and right-to-left (RTL)
is the default layout direction. English is a secondary toggle.

- The HTML `dir` attribute MUST default to `rtl`.
- All layouts MUST use CSS logical properties (`margin-inline-start`,
  `padding-inline-end`) instead of physical properties
  (`margin-left`, `padding-right`).
- Typography MUST use IBM Plex Arabic as the primary font, with
  IBM Plex Sans as the Latin fallback and IBM Plex Mono for amounts
  and codes.
- Numeric amounts MUST render in LTR direction with tabular-nums
  regardless of the document direction.
- Every user-visible string MUST be externalized via react-i18next
  with Arabic (`ar`) and English (`en`) namespaces.

### III. Multi-Tenant Data Isolation

Every tenant-scoped database record MUST include a `company_id` column.
Cross-tenant data leakage is a critical security failure.

- Every database query that returns tenant-scoped data MUST filter by
  `company_id` extracted from the authenticated user's JWT token.
- A shared FastAPI dependency MUST inject the tenant scope; direct
  queries that bypass this dependency are forbidden.
- Automated tests MUST verify that queries scoped to one tenant return
  zero results for another tenant's data.
- PostgreSQL Row-Level Security (RLS) SHOULD be applied as a
  defense-in-depth layer once the schema stabilizes.

### IV. Field-Worker UX Priority

The primary user is a field worker on a construction site, outdoor event,
or freight yard. The interface MUST be optimized for speed, glare, and
gloved hands.

- Touch targets MUST be a minimum of 44x44 CSS pixels.
- The critical path from app open to expense submitted MUST complete
  in under 15 seconds.
- Navigation depth MUST NOT exceed 3 taps for any primary action.
- Dark mode MUST be the default theme to reduce battery drain on OLED
  screens and improve outdoor readability.
- High-contrast color ratios MUST meet WCAG AA for all text and
  interactive elements.
- No decorative illustrations, card-in-card nesting, or rounded-square
  icon tiles on functional screens.

### V. Spec-Driven Development

No feature code is written without a preceding specification. The
Spec-Kit workflow is mandatory for every feature and phase.

- Every feature MUST begin with `/speckit.specify` to produce a `spec.md`.
- A `/speckit.plan` MUST generate the technical plan before implementation.
- A `/speckit.tasks` MUST break the plan into ordered, dependency-aware
  tasks before any code is written.
- The constitution MUST be consulted during the plan's Constitution Check
  gate. Violations MUST be documented and justified in the Complexity
  Tracking table.
- Specifications are the contract between intent and implementation.
  Ambiguities MUST be resolved via `/speckit.clarify` before planning.

### VI. Security by Default

The application handles financial data for enterprise clients. Security
is non-negotiable at every layer.

- Authentication MUST use JWT tokens with bcrypt-hashed passwords.
- All production traffic MUST be served over HTTPS with TLS 1.2+.
- Docker containers MUST run as non-root users in production.
- Secrets (API keys, database passwords, VAPID keys) MUST NEVER be
  committed to source control; they MUST be injected via environment
  variables or `.env` files with restrictive permissions (600).
- All user-uploaded files (receipts, voice recordings) MUST be stored
  in Cloudflare R2 with signed URLs; direct public access is forbidden.
- OpenAI API calls MUST be rate-limited via Redis to prevent cost
  overruns and API throttling.

## Technology Stack Constraints

The following technology choices are locked for the duration of the
project. Changes require a constitution amendment.

**Frontend**: React 19.2, TypeScript 6.0, Vite 8 (Rolldown), Tailwind
CSS 4, shadcn/ui (RTL mode), Dexie.js 4.4, React Router 7, Zustand 5,
react-i18next 15, React Hook Form 7, vite-plugin-pwa 0.21

**Backend**: Python 3.13, FastAPI 0.136, SQLAlchemy 2.0 (async),
Pydantic 2.13, Alembic 1.14, Uvicorn 0.34

**Database & Storage**: PostgreSQL 16, Redis 7, Cloudflare R2

**Infrastructure**: Docker + Compose, Nginx 1.27, Certbot, Ubuntu 24.04
LTS (production VPS)

**Package Managers**: pnpm 9 (frontend), uv (backend)

**AI Services**: OpenAI gpt-4o-mini-transcribe (voice), OpenAI gpt-4o
(receipt OCR), pyzbar + Pillow (QR decode)

## Development Workflow

All development follows this sequence:

1. **Specify** — Define what and why (`/speckit.specify`)
2. **Clarify** — Resolve ambiguities (`/speckit.clarify`)
3. **Plan** — Define how, with constitution check (`/speckit.plan`)
4. **Tasks** — Break into ordered implementation steps (`/speckit.tasks`)
5. **Analyze** — Cross-artifact consistency check (`/speckit.analyze`)
6. **Implement** — Execute tasks in order (`/speckit.implement`)

Additional workflow rules:

- Local development uses Docker Compose (PostgreSQL, Redis, API).
- The frontend dev server proxies `/api` to the backend container.
- Git commits follow conventional commits format.
- Impeccable design audits (`/impeccable audit`) MUST pass before
  merging any UI-facing changes.
- Each completed phase ends with a checklist validation.

## Governance

This constitution is the highest-authority document in the ENGEZ project.
It supersedes all other practices, conventions, and ad-hoc decisions.

- **Amendments** require: (1) written justification, (2) impact analysis
  on existing specs and plans, (3) version increment, and (4) update to
  all dependent templates.
- **Version format** follows semantic versioning:
  - MAJOR: principle removed, redefined, or fundamentally altered.
  - MINOR: new principle or section added, or material expansion.
  - PATCH: wording clarification, typo fix, non-semantic refinement.
- **Compliance review**: every `/speckit.plan` execution MUST include a
  Constitution Check gate that verifies the proposed design against all
  principles listed above. Violations MUST be justified in the plan's
  Complexity Tracking table.
- **Runtime guidance**: refer to `CLAUDE.md` and plan files in `files/`
  for implementation-level development guidance.

**Version**: 1.0.0 | **Ratified**: 2026-05-15 | **Last Amended**: 2026-05-15

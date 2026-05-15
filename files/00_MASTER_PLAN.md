# ENGEZ PWA — Master Development Plan

## For AI-Assisted Implementation via Spec-Kit + Claude Code + Impeccable

**Target:** Egyptian Enterprise Sector — Construction, Event Management, Freight Logistics
**Developer:** Solo developer on Windows 11 / VSCode / Docker Desktop
**Production:** Self-managed VPS (Ubuntu 24.04 LTS)
**Date:** May 2026

---

## Document Index

This plan is split into focused files for manageable context windows:

| File | Contents |
|------|----------|
| `00_MASTER_PLAN.md` | This file — overview, validated stack, environment setup |
| `01_PHASE1_FOUNDATION.md` | Weeks 1–3: Scaffold, Design System, Auth, Schema, Spec-Kit commands |
| `02_PHASE2_CORE_CAPTURE.md` | Weeks 4–7: Voice, Receipt OCR, ETA QR, Expense Form, Offline Sync |
| `03_PHASE3_REVIEW_DESK.md` | Weeks 8–10: Accountant Queue, AI Feedback Loop, Push Notifications |
| `04_PHASE4_INTEGRATION.md` | Weeks 11–14: Accounting Export, Analytics Dashboard, Anomaly Detection |
| `05_DEPLOYMENT_OPS.md` | Docker Compose production config, Nginx, SSL, CI/CD, VPS hardening |
| `06_KNOWN_CONFLICTS.md` | Pre-identified dependency conflicts and their resolutions |

---

## Validated Technology Stack (As of May 2026)

Every version below has been verified against current npm/PyPI registries.

### Frontend

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Framework | React | 19.2.x | Stable, React Compiler ready, ref cleanup functions |
| Language | TypeScript | 6.0.x | Stable production default (TS 7 beta — skip for now) |
| Bundler | Vite | 8.x | Rolldown-powered, instant HMR, `@vitejs/plugin-react` v6 |
| PWA | vite-plugin-pwa | 0.21.x | Workbox 7 integration, generateSW + injectManifest |
| Offline DB | Dexie.js | 4.4.x | IndexedDB wrapper, IDB 3.0 optimizations, Blob offloading |
| Routing | React Router | 7.x | Nested routes, loaders, `/field/*` and `/accountant/*` groups |
| UI Components | shadcn/ui | latest | First-class RTL support (Jan 2026), Radix UI primitives |
| CSS | Tailwind CSS | 4.x | Utility-first, logical properties for RTL via shadcn CLI |
| i18n | react-i18next | 15.x | Arabic RTL default, English toggle, namespace splitting |
| State | Zustand | 5.x | Lightweight, persist middleware, devtools integration |
| Forms | React Hook Form | 7.x | Performance-focused, minimal re-renders |
| Charts | Recharts | 2.x | React-native charting for analytics dashboard |

### Design Skill (AI Harness)

| Tool | Version | Purpose |
|------|---------|---------|
| Impeccable | latest | Design skill for Claude Code — `/impeccable polish`, `/impeccable audit`, product mode for app UI |
| Font Stack | IBM Plex Arabic + IBM Plex Sans | Arabic-first typography, paired Latin fallback |

### Backend

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Framework | FastAPI | 0.136.x | Python 3.13 support, async-first, Pydantic v2 |
| Runtime | Python | 3.13.x | Latest stable, PEP 695 generics, performance gains |
| Validation | Pydantic | 2.13.x | 50x faster validation vs v1, native FastAPI integration |
| Auth | python-jose + passlib | latest | JWT RS256 tokens, bcrypt password hashing |
| ORM | SQLAlchemy | 2.0.x | Async sessions, type-safe queries |
| Migrations | Alembic | 1.14.x | Auto-generate from SQLAlchemy models |
| ASGI Server | Uvicorn | 0.34.x | Production ASGI, HTTP/2, `--workers` for multiprocess |
| Voice AI | OpenAI API | gpt-4o-mini-transcribe | Egyptian Arabic transcription |
| Vision AI | OpenAI API | gpt-4o | Receipt OCR, Arabic/English extraction |
| QR Decode | pyzbar + Pillow | latest | ETA e-invoice QR decoding from receipt photos |
| Push | pywebpush + py-vapid | latest | Web Push notifications |

### Database & Storage

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Database | PostgreSQL | 16.x | JSONB for AI metadata, full-text search |
| Cache | Redis | 7.x | Session cache, rate limiting, pub/sub for notifications |
| Object Storage | Cloudflare R2 | — | S3-compatible, zero egress fees, receipt image storage |

### DevOps & Infrastructure

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Containerization | Docker + Compose | 27.x / 2.x | Local dev parity with production |
| Reverse Proxy | Nginx | 1.27.x | SSL termination, static file serving, gzip |
| SSL | Certbot (Let's Encrypt) | latest | Auto-renewal, wildcard certs |
| Process Manager | systemd | — | Docker Compose service management on VPS |

### Development Tools

| Tool | Version | Purpose |
|------|---------|---------|
| Spec-Kit (GitHub) | latest (`specify-cli`) | Spec-Driven Development workflow |
| Impeccable | latest | AI design skill for Claude Code |
| Claude Code | latest | Primary AI coding agent |
| VSCode | latest | Primary IDE on Windows |
| Docker Desktop | latest | Windows container runtime |
| Node.js | 22.x LTS | Frontend build toolchain |
| pnpm | 9.x | Fast, disk-efficient package manager |

---

## Local Development Environment Setup

### Prerequisites (Windows 11)

```powershell
# 1. Install Node.js 22 LTS
winget install OpenJS.NodeJS.LTS

# 2. Install pnpm
corepack enable
corepack prepare pnpm@latest --activate

# 3. Install Python 3.13
winget install Python.Python.3.13

# 4. Install Docker Desktop
winget install Docker.DockerDesktop

# 5. Install uv (Python package manager — replaces pip for speed)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 6. Install Claude Code (for Spec-Kit integration)
npm install -g @anthropic-ai/claude-code

# 7. Install Spec-Kit CLI
uv tool install specify-cli --from git+https://github.com/github/spec-kit@latest

# 8. Verify installations
node --version        # v22.x.x
pnpm --version        # 9.x.x
python --version      # Python 3.13.x
docker --version      # Docker 27.x.x
uv --version          # 0.x.x
speckit --help        # Should show Spec-Kit commands
```

### Project Directory Structure

```
field-expense-pwa/
├── .specify/                    # Spec-Kit artifacts
│   ├── memory/
│   │   └── constitution.md      # Project non-negotiables
│   └── specs/
│       └── 001-field-expense/
│           ├── spec.md          # Feature specification
│           ├── plan.md          # Technical plan
│           ├── data-model.md    # Schema design
│           ├── research.md      # Tech research
│           ├── quickstart.md    # Setup instructions
│           └── tasks.md         # Implementation tasks
├── .claude/                     # Claude Code skills
│   └── skills/                  # Impeccable design skills
├── .impeccable.md               # Brand/product design config
├── frontend/                    # React PWA
│   ├── src/
│   │   ├── components/
│   │   │   └── ui/             # shadcn/ui components (RTL)
│   │   ├── features/
│   │   │   ├── field/          # Field worker screens
│   │   │   ├── accountant/     # Accountant screens
│   │   │   └── admin/          # Admin screens
│   │   ├── lib/
│   │   │   ├── db.ts           # Dexie.js schema
│   │   │   ├── api.ts          # API client
│   │   │   ├── auth.ts         # Auth context
│   │   │   └── i18n.ts         # i18n config
│   │   ├── hooks/              # Custom React hooks
│   │   ├── stores/             # Zustand stores
│   │   └── sw/                 # Service worker (injectManifest)
│   ├── public/
│   │   └── locales/            # i18n JSON files
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── components.json         # shadcn/ui config (rtl: true)
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── expenses.py
│   │   │   │   ├── projects.py
│   │   │   │   ├── voice.py
│   │   │   │   └── receipts.py
│   │   │   └── deps.py         # Dependency injection
│   │   ├── core/
│   │   │   ├── config.py       # Pydantic Settings
│   │   │   ├── security.py     # JWT + hashing
│   │   │   └── database.py     # Async SQLAlchemy
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   │   ├── ai_voice.py
│   │   │   ├── ai_receipt.py
│   │   │   ├── qr_decode.py
│   │   │   └── anomaly.py
│   │   └── main.py             # FastAPI app factory
│   ├── alembic/                # Database migrations
│   ├── tests/
│   ├── pyproject.toml          # uv/pip project config
│   └── Dockerfile
├── docker-compose.yml          # Local dev stack
├── docker-compose.prod.yml     # Production stack
├── nginx/
│   ├── nginx.conf
│   └── conf.d/
│       └── app.conf
├── PRODUCT.md                  # Impeccable product identity
└── README.md
```

---

## Spec-Kit Workflow Overview

Every phase begins with Spec-Kit commands to generate structured specifications before any code is written. This ensures Claude Code has precise, unambiguous instructions.

### One-Time Project Setup

```bash
# Initialize Spec-Kit with Claude Code integration
cd field-expense-pwa
speckit init field-expense-pwa --integration claude-code

# Install Impeccable design skills
npx impeccable skills add pbakaus/impeccable

# Create project constitution (run ONCE)
# Then type /speckit.constitution in Claude Code
```

### Per-Phase Workflow

```bash
# 1. Write specification (what + why, no tech details)
/speckit.specify

# 2. Clarify ambiguities (optional but recommended)
/speckit.clarify

# 3. Generate technical plan (tech stack + architecture)
/speckit.plan

# 4. Break into ordered tasks
/speckit.tasks

# 5. Analyze for consistency
/speckit.analyze

# 6. Execute implementation
/speckit.implement
```

---

## Impeccable Configuration

Create `.impeccable.md` in project root:

```markdown
# Product Identity

## Mode
product

## Name
Masrouf (مصروف) — Field Expense PWA

## Voice
Professional, efficient, bilingual (Arabic-first, English-second).
Direct and trustworthy — this handles money.

## Typography
- Primary: IBM Plex Arabic (Arabic text)
- Secondary: IBM Plex Sans (English text, numbers)
- Monospace: IBM Plex Mono (amounts, codes)

## Color System
- Brand: Deep teal (#0D9488) — trust, finance
- Accent: Amber (#F59E0B) — warnings, pending states
- Success: Emerald (#10B981) — approved
- Danger: Rose (#F43F5E) — rejected, fraud flags
- Surface: Neutral grays, dark mode default

## Anti-References
- No purple gradients
- No card-in-card nesting
- No decorative illustrations on functional screens
- No rounded-square icon tiles above headings
- No Inter font

## Design Constraints
- RTL-first: all layouts must work in Arabic RTL
- Touch targets: minimum 44x44px (field workers wear gloves)
- High contrast: receipts viewed in outdoor sunlight
- Minimal navigation: 3 taps maximum to submit expense
- Dark mode default: reduces battery on OLED field devices
```

---

## Next Steps

Proceed to `01_PHASE1_FOUNDATION.md` for the detailed Phase 1 implementation plan.

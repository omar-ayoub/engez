# Implementation Plan: Core Expense Capture

**Branch**: `002-core-expense-capture` | **Date**: 2026-05-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-core-expense-capture/spec.md`

## Summary

Build the four-mode expense capture system (voice, receipt, combined, manual) with offline-first architecture and background sync. Voice capture uses the browser MediaRecorder API (webm/opus) with OpenAI gpt-4o-mini-transcribe for Egyptian Arabic dialect transcription and GPT-4o-mini for structured field extraction, seeded with per-company correction history as few-shot examples (the compounding moat). Receipt capture uses canvas-based client-side compression (max 1200px, JPEG 0.85) and GPT-4o vision for OCR, with pyzbar for ETA QR code decoding — providing zero-typing submission for compliant Egyptian tax receipts. All capture modes write to IndexedDB via Dexie.js before any network request. The service worker is upgraded from generateSW to injectManifest for custom Background Sync logic with exponential backoff. Offline-captured voice/receipt blobs follow a draft-hold workflow: blobs are uploaded for AI processing when connectivity returns, and the user must review and confirm before submission.

## Technical Context

**Language/Version**: Frontend: TypeScript 6.0 on React 19.2 | Backend: Python 3.13

**Primary Dependencies**:
- Frontend: (Phase 1 stack) + dexie-react-hooks 1.1 (live queries for sync status and draft counts)
- Backend: (Phase 1 stack) + openai 1.x (gpt-4o-mini-transcribe, gpt-4o vision), pyzbar 0.23 (QR decode), Pillow 11.x (image preprocessing for faded thermal receipts), boto3 1.x (Cloudflare R2 S3-compatible SDK)

**Storage**: PostgreSQL 16 (expenses, corrections, vendor cache), Redis 7 (AI call rate limiting), IndexedDB via Dexie.js (offline drafts + blobs), Cloudflare R2 (receipt images, voice recordings — signed URLs only)

**Testing**: Vitest + Testing Library React (frontend) | pytest + pytest-asyncio + httpx (backend)

**Target Platform**: PWA on modern browsers (Android 8+ Chrome/Samsung Internet, iOS 14+ Safari)

**Project Type**: Web application (frontend PWA + backend API)

**Performance Goals**:
- Voice extraction: <5s from recording end to pre-filled form (online)
- Receipt compression: <300KB in 95%+ of cases
- Expense submission: <15s from app open (voice capture flow)
- Offline sync: <30s after reconnect (manual expenses auto-sync)
- Deferred AI processing: <60s after reconnect (voice/receipt drafts)

**Constraints**: Offline-capable (all 4 capture modes), RTL-first, 44px min touch targets, dark mode default, WCAG AA, multi-tenant isolation via company_id, rate-limited AI calls via Redis

**Scale/Scope**: Same as Phase 1 — dozens of companies, hundreds of users per company. Expected AI calls: ~50-200 per company per day.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
| --------- | ------ | -------- |
| I. Offline-First Architecture | PASS | All 4 capture modes write to IndexedDB before any network request. Voice/receipt blobs stored locally as Dexie Blob fields. Sync queue with Background Sync API + 30s polling fallback for Safari/iOS. Service worker precaches app shell via injectManifest. Draft-hold workflow ensures offline voice/receipt data is never lost. 7-day local retention for unsynced items. |
| II. Arabic-First RTL | PASS | Amount fields use LTR + tabular-nums (existing pattern). Category icon grid has ar/en labels via i18n. Vendor autocomplete searches Arabic names. Voice transcription targets Egyptian Arabic dialect with domain-specific prompt. All new UI strings externalized via react-i18next ar/en namespaces. |
| III. Multi-Tenant Data Isolation | PASS | All new API endpoints filter by company_id from JWT via `get_tenant_scope` dependency. AI extraction prompts include company-scoped few-shot examples. Vendor cache scoped per company_id. Rate limiting keyed by company_id. No cross-tenant data in any query. |
| IV. Field-Worker UX Priority | PASS | One-tap voice capture (single button). Receipt photo via native camera (`capture=environment`). Large submit button (56px, full-width, thumb-reachable). Category icon grid (not dropdown — faster for touch). Auto-save every 5s. <15s critical path measured. 44px touch targets on all new interactive elements. Dark mode default. |
| V. Spec-Driven Development | PASS | Following specify -> clarify -> plan -> tasks workflow. Clarified spec with 3 decisions encoded (AI latency, draft-hold, required fields). |
| VI. Security by Default | PASS | Voice/receipt blobs stored in Cloudflare R2 with signed URLs — no direct public access. OpenAI API calls rate-limited via Redis sliding window per company_id. File upload size limits enforced server-side (10MB voice, 10MB receipt raw). Audio/image content validated before processing. All endpoints require JWT authentication. |

**Gate result: ALL PASS** — no violations, no complexity tracking entries needed.

**Post-design re-check**: ALL PASS confirmed. The injectManifest migration is a standard PWA upgrade, not a constitution violation. No new principles are strained.

## Project Structure

### Documentation (this feature)

```text
specs/002-core-expense-capture/
├── plan.md              # This file
├── spec.md              # Feature specification (clarified)
├── research.md          # Phase 0: technology decisions
├── data-model.md        # Phase 1: schema changes and entity updates
├── quickstart.md        # Phase 1: new dependencies and setup
├── contracts/           # Phase 1: API contracts
│   ├── voice.md         # Voice capture extraction API
│   ├── receipts.md      # Receipt OCR + QR decode API
│   ├── expenses.md      # Expense CRUD API
│   └── vendors.md       # Vendor autocomplete API
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Created by /speckit-tasks (not by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/v1/
│   │   ├── voice.py             # POST /voice/extract
│   │   ├── receipts.py          # POST /receipts/extract
│   │   ├── expenses.py          # POST/GET/PATCH /expenses
│   │   └── vendors.py           # GET /vendors/search
│   ├── schemas/
│   │   ├── expense.py           # Expense CRUD + AI extraction response schemas
│   │   ├── voice.py             # Voice extraction response schema
│   │   ├── receipt.py           # Receipt extraction + QR response schema
│   │   └── vendor.py            # Vendor search response schema
│   ├── services/
│   │   ├── ai_voice.py          # Whisper transcription + GPT-4o-mini extraction
│   │   ├── ai_receipt.py        # GPT-4o vision OCR + merge with QR
│   │   ├── qr_decode.py         # ETA QR code decoding (pyzbar + Pillow)
│   │   ├── r2_storage.py        # Cloudflare R2 upload + signed URL generation
│   │   └── rate_limiter.py      # Redis sliding window per company_id
│   └── models/
│       └── expense.py           # Updated: +items, +capture_mode, +voice_url; category_id nullable
├── alembic/versions/
│   └── xxxx_add_capture_fields.py  # Migration for new columns
├── tests/
│   ├── test_voice_extract.py    # Voice extraction endpoint + AI pipeline
│   ├── test_receipt_extract.py  # Receipt OCR + QR decode integration
│   ├── test_qr_decode.py        # ETA QR parsing unit tests
│   ├── test_expenses.py         # Expense CRUD + sync endpoints
│   └── test_rate_limiter.py     # Rate limiting logic tests
└── pyproject.toml               # +openai, +pyzbar, +Pillow, +boto3

frontend/
├── src/
│   ├── features/
│   │   └── capture/
│   │       ├── hooks/
│   │       │   ├── useVoiceCapture.ts      # MediaRecorder lifecycle (start/stop/auto-stop)
│   │       │   ├── useReceiptCapture.ts    # Camera trigger + canvas compression
│   │       │   ├── useDraftProcessor.ts    # Process offline drafts when online
│   │       │   └── useExpenseForm.ts       # React Hook Form + auto-save + submit
│   │       ├── components/
│   │       │   ├── VoiceRecordButton.tsx   # Animated record button with duration
│   │       │   ├── ReceiptCamera.tsx       # Camera input + preview thumbnail
│   │       │   ├── ExpenseForm.tsx         # Main form: amount, vendor, items, category, project
│   │       │   ├── CategoryGrid.tsx        # 2x4 icon grid for category selection
│   │       │   ├── VendorAutocomplete.tsx  # Fuzzy search over local vendor cache
│   │       │   ├── ConfidenceBadge.tsx     # Green/amber/red confidence indicator
│   │       │   └── DraftReviewBanner.tsx   # "N drafts ready for review" notification
│   │       └── pages/
│   │           ├── CapturePage.tsx         # Capture mode selector + form
│   │           └── DraftReviewPage.tsx     # List + review AI-processed drafts
│   ├── sw/
│   │   └── service-worker.ts              # Custom SW: precache + Background Sync + blob upload
│   ├── hooks/
│   │   └── useSyncStatus.ts               # Live sync status + pending/draft counts
│   └── lib/
│       ├── db.ts                          # Dexie schema v2: +items, +captureMode, +vendorCache table
│       ├── sync.ts                        # Updated: blob upload queue + draft processing
│       └── image-compress.ts              # Canvas-based receipt compression utility
├── public/locales/
│   ├── ar/capture.json                    # Arabic capture UI strings
│   └── en/capture.json                    # English capture UI strings
└── package.json                           # +dexie-react-hooks
```

**Structure Decision**: Extends the Phase 1 web application layout. New capture features organized under `frontend/src/features/capture/` following a feature-module pattern to keep capture concerns isolated from the existing app shell. Backend adds new API routes, services, and schemas alongside existing Phase 1 code. The service worker moves from auto-generated (workbox generateSW) to custom (injectManifest) to support Background Sync with blob upload logic.

## Complexity Tracking

> No constitution violations detected. Table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | — | — |

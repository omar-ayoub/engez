# Tasks: Core Expense Capture

**Input**: Design documents from `/specs/002-core-expense-capture/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in the specification. Test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/app/` (FastAPI, Python 3.13)
- **Frontend**: `frontend/src/` (React 19, TypeScript, Vite)
- **Migrations**: `backend/alembic/versions/`
- **i18n**: `frontend/public/locales/{ar,en}/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install new dependencies, configure environment, and scaffold shared infrastructure

- [X] T001 Add backend dependencies to `backend/pyproject.toml`: openai>=1.40,<2, pyzbar==0.23.0, Pillow>=11.0,<12, boto3>=1.35,<2. Run `cd backend && uv sync`
- [X] T002 [P] Add frontend dependency dexie-react-hooks@^1.1 to `frontend/package.json`. Run `cd frontend && pnpm install`
- [X] T003 [P] Add libzbar0 system package to backend Dockerfile: `RUN apt-get update && apt-get install -y libzbar0 && rm -rf /var/lib/apt/lists/*` in `backend/Dockerfile`
- [X] T004 [P] Add new environment variables to `backend/app/core/config.py`: OPENAI_API_KEY, R2_ACCOUNT_ID, R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET, R2_PUBLIC_URL, AI_RATE_LIMIT_VOICE (default 100), AI_RATE_LIMIT_RECEIPT (default 100). Update `.env.example` with the same keys
- [X] T005 [P] Create i18n capture namespace files with Arabic and English strings for capture UI (voice, receipt, form, categories, sync status, draft review) in `frontend/public/locales/ar/capture.json` and `frontend/public/locales/en/capture.json`
- [X] T006 [P] Update `frontend/vite.config.ts` to switch VitePWA from generateSW to injectManifest strategy: set `strategies: "injectManifest"`, `srcDir: "src/sw"`, `filename: "service-worker.ts"`, remove existing `workbox.runtimeCaching` config, add `injectManifest: { globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"] }`, add `devOptions: { enabled: true, type: "module" }`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database migrations, shared services, core API endpoints, and basic form infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Create Alembic migration `backend/alembic/versions/xxxx_add_capture_fields.py`: add `items` column (TEXT, NOT NULL, server_default=''), add `capture_mode` column (VARCHAR(20), NOT NULL, server_default='manual'), add `voice_url` column (VARCHAR(500), nullable), alter `category_id` to nullable. Existing rows keep their category_id values
- [X] T008 [P] Update Expense SQLAlchemy model in `backend/app/models/expense.py`: add `items` column (String, nullable=False, server_default=''), add `capture_mode` column (String(20), nullable=False, server_default='manual'), add `voice_url` column (String(500), nullable=True), change `category_id` to nullable=True in the relationship
- [X] T009 [P] Create expense Pydantic schemas in `backend/app/schemas/expense.py`: ExpenseCreate (offline_id, amount, currency, vendor, vendor_tax_reg, items, category_id, project_id, notes, capture_mode, voice_url, voice_transcript, receipt_url, eta_uuid, eta_verified, ai_extraction, ai_confidence), ExpenseResponse (id, offline_id, status, synced_at, created_at), ExpenseListResponse (items, total, page, per_page, pages), ExpensePatch (partial update fields)
- [X] T010 [P] Create Cloudflare R2 storage service in `backend/app/services/r2_storage.py`: async `upload_blob` function using boto3 S3 client, key format `{company_id}/{type}/{YYYY-MM}/{uuid}.{ext}`, return signed URL with 1-hour expiry. Use settings from config.py for R2 credentials
- [X] T011 [P] Create Redis rate limiter service in `backend/app/services/rate_limiter.py`: async `check_rate_limit` function using Redis INCR + EXPIRE sliding window approximation, keyed by `ratelimit:{company_id}:{endpoint}:{window}`, configurable limits from config.py (AI_RATE_LIMIT_VOICE, AI_RATE_LIMIT_RECEIPT). Raise HTTPException 429 with Arabic/English detail when exceeded
- [X] T012 Create expense API router in `backend/app/api/v1/expenses.py`: POST /expenses (create with offline_id dedup → 409 on conflict, auto-create CorrectionFeedback when PATCH modifies AI-extracted fields), GET /expenses (list with status/capture_mode/date/project_id filters and pagination), PATCH /expenses/{id} (partial update with correction feedback auto-creation). All endpoints use get_current_user and get_db dependencies, filter by company_id for multi-tenant isolation
- [X] T013 Register new API routers in `backend/app/api/v1/__init__.py` or main app file: include voice router (prefix=/voice), receipts router (prefix=/receipts), expenses router (prefix=/expenses), vendors router (prefix=/vendors) — routers will be created in later phases, add placeholder imports
- [X] T014 [P] Update Dexie schema to v2 in `frontend/src/lib/db.ts`: add `captureMode` index to expenses table, add new `vendorCache` table with indexes `id, companyId, name, nameAr, taxRegistration`, add upgrade function that sets `captureMode` to 'manual', `items` to '', and `draftProcessed` to false on existing expense records. Define OfflineExpense and OfflineVendor TypeScript interfaces per data-model.md
- [X] T015 [P] Create basic useExpenseForm hook in `frontend/src/features/capture/hooks/useExpenseForm.ts`: React Hook Form 7 integration with all expense fields (amount, currency, vendor, items, category_id, project_id, notes), auto-save draft to Dexie every 5 seconds via setInterval when form is dirty, onSubmit changes status to "pending" and adds to syncQueue, accepts optional initial data for pre-fill from AI extraction
- [X] T016 [P] Create basic ExpenseForm component in `frontend/src/features/capture/components/ExpenseForm.tsx`: renders all expense fields connected to useExpenseForm hook, amount field with monospace LTR styling, vendor text input, items text input, category dropdown (placeholder — replaced by icon grid in US3), project select, notes textarea, submit button. Accepts `initialData` prop for AI pre-fill. Uses react-i18next for labels from capture namespace

**Checkpoint**: Foundation ready — database migrated, API endpoints functional, basic form renders. User story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Voice Expense Capture (Priority: P1) 🎯 MVP

**Goal**: Field worker taps one button, speaks in Egyptian Arabic, and the form auto-fills with extracted expense data within 5 seconds

**Independent Test**: Record a voice clip in Egyptian Arabic dialect and verify the form auto-fills with correct amount, category, vendor, and confidence indicators

### Implementation for User Story 1

- [X] T017 [P] [US1] Create voice extraction Pydantic schemas in `backend/app/schemas/voice.py`: VoiceExtractionResponse with fields transcript (str), extraction (object with amount, currency, category, vendor, items, project_hint, confidence), voice_url (str). Confidence is an object with 0-1 scores per field
- [X] T018 [P] [US1] Create AI voice extraction service in `backend/app/services/ai_voice.py`: async `transcribe_and_extract` function — (1) call OpenAI gpt-4o-mini-transcribe with audio bytes, language="ar", Egyptian Arabic domain prompt with common expense words, (2) call async `get_few_shot_examples` to fetch up to 10 recent CorrectionFeedback records for the company ordered by created_at desc, (3) call gpt-4o-mini with response_format json_object and system prompt for expense extraction including few-shot examples and active project names, (4) return transcript + extraction + confidence. Use AsyncOpenAI client from settings.OPENAI_API_KEY
- [X] T019 [US1] Create voice API endpoint in `backend/app/api/v1/voice.py`: POST /voice/extract — accepts audio UploadFile (max 10MB, audio/* MIME), validates size, uploads audio blob to R2 via r2_storage.upload_blob, fetches active project names for company (Project.name_ar + Project.name where is_active), calls ai_voice.transcribe_and_extract, applies rate limiting via rate_limiter.check_rate_limit. Returns VoiceExtractionResponse. Handle empty transcription → 422 with Arabic/English detail
- [X] T020 [P] [US1] Create useVoiceCapture hook in `frontend/src/features/capture/hooks/useVoiceCapture.ts`: MediaRecorder lifecycle hook — request microphone with echoCancellation + noiseSuppression + sampleRate 16000, prefer webm/opus MIME type (fallback to audio/webm), start recording with 250ms chunk interval, track duration with setInterval, auto-stop at 60 seconds max, return { isRecording, duration, start, stop } where stop returns Promise<{ blob, duration }>. Release microphone tracks on stop
- [X] T021 [P] [US1] Create VoiceRecordButton component in `frontend/src/features/capture/components/VoiceRecordButton.tsx`: animated record button with pulsing indicator while recording, displays elapsed duration in mm:ss format, tap to start/stop, uses useVoiceCapture hook. On stop, sends audio blob to POST /api/v1/voice/extract as multipart/form-data, shows loading spinner during AI processing, calls onExtraction callback with result (transcript + extraction + confidence). Handles errors (no mic permission, network failure). 44px minimum touch target. Uses i18n for Arabic labels
- [X] T022 [US1] Wire VoiceRecordButton to ExpenseForm in `frontend/src/features/capture/components/ExpenseForm.tsx`: add VoiceRecordButton above the form, pass onExtraction callback that maps extraction fields to form defaults (amount, vendor, items, category, project_hint), pass confidence scores to form for field highlighting. When voice extraction completes, form fields populate and user can edit before submitting

**Checkpoint**: Voice capture fully functional — record button captures audio, backend transcribes Egyptian Arabic and extracts expense fields, form pre-fills within 5 seconds. MVP deliverable.

---

## Phase 4: User Story 2 - Receipt Photo Capture with QR Decode (Priority: P2)

**Goal**: Field worker photographs a receipt, AI extracts text (Arabic/English), ETA QR codes decode to auto-fill verified tax data with zero typing

**Independent Test**: Photograph an Arabic thermal receipt with and without ETA QR code, verify form fields populate correctly with QR data overriding OCR data

### Implementation for User Story 2

- [X] T023 [P] [US2] Create receipt extraction Pydantic schemas in `backend/app/schemas/receipt.py`: ReceiptExtractionResponse with fields extraction (object with amount, currency, vendor, vendor_tax_reg, date, category, items, line_items, confidence), qr_detected (bool), qr_data (optional object with uuid, total, issuer_rin, datetime), receipt_url (str)
- [X] T024 [P] [US2] Create ETA QR decode service in `backend/app/services/qr_decode.py`: `decode_eta_qr` function accepts image bytes, opens with Pillow, attempts pyzbar decode on original image, on failure retries with grayscale + 2x contrast enhancement (Pillow ImageEnhance). Parses decoded QR data with regex matching ETA URL pattern `receipts/search/{UUID}/share/{DateTime}#Total:{Total},IssuerRIN:{RIN}`. Returns ETAQRData dataclass (uuid, total, issuer_rin, datetime, raw_url) or None
- [X] T025 [US2] Create AI receipt processing service in `backend/app/services/ai_receipt.py`: async `process_receipt` function — (1) call qr_decode.decode_eta_qr on image bytes (instant, no API), (2) base64 encode image and send to GPT-4o vision with detail="high" and Arabic/English receipt OCR system prompt requesting JSON with amount, currency, vendor, date, category, items, line_items, confidence, (3) merge results: QR data overrides OCR for amount, vendor_tax_reg, date, eta_uuid. If QR issuer_rin matches VendorCache entry, use cached vendor name and category_hint. Return merged extraction + qr_detected + qr_data
- [X] T026 [US2] Create receipts API endpoint in `backend/app/api/v1/receipts.py`: POST /receipts/extract — accepts image UploadFile (max 10MB, image/* MIME), validates size, uploads image to R2, calls ai_receipt.process_receipt, applies rate limiting. Returns ReceiptExtractionResponse. Handle unreadable receipt → 422 with Arabic/English detail
- [X] T027 [P] [US2] Create image compression utility in `frontend/src/lib/image-compress.ts`: async `compressReceiptImage` function — loads File into Image element, draws on canvas scaled to max 1200px longest edge preserving aspect ratio, exports as JPEG quality 0.85 via canvas.toBlob. Target: 95%+ images under 300KB
- [X] T028 [P] [US2] Create useReceiptCapture hook in `frontend/src/features/capture/hooks/useReceiptCapture.ts`: manages camera input trigger and image processing — accepts HTML5 input[type=file][capture=environment] change event, compresses image via compressReceiptImage, returns { imageBlob, previewUrl, capture, reset }. Preview URL via URL.createObjectURL for thumbnail display
- [X] T029 [P] [US2] Create ReceiptCamera component in `frontend/src/features/capture/components/ReceiptCamera.tsx`: camera trigger button with receipt icon, hidden file input with capture=environment and accept="image/*", on file select compresses image, shows preview thumbnail, sends compressed image to POST /api/v1/receipts/extract, loading spinner during AI processing, calls onExtraction callback with result. Shows "QR detected" badge when qr_detected is true. Handles camera permission errors. 44px touch target
- [X] T030 [US2] Wire ReceiptCamera to ExpenseForm in `frontend/src/features/capture/components/ExpenseForm.tsx`: add ReceiptCamera alongside VoiceRecordButton, map receipt extraction to form defaults with QR data taking precedence over OCR data, pass confidence scores. Show "ETA verified" badge when qr_detected is true

**Checkpoint**: Receipt capture fully functional — camera triggers, image compresses, AI extracts text from Arabic/English receipts, ETA QR codes decode with tax data, form pre-fills correctly.

---

## Phase 5: User Story 3 - Expense Form and Submission (Priority: P3)

**Goal**: Polished mobile-first expense form with category icon grid, vendor autocomplete, confidence indicators, auto-save, and one-tap submit — total flow under 15 seconds

**Independent Test**: Manually enter all fields and submit, verify form saves, submits, and queues for sync. Test autocomplete and category grid.

### Implementation for User Story 3

- [X] T031 [P] [US3] Create CategoryGrid component in `frontend/src/features/capture/components/CategoryGrid.tsx`: 2x4 visual icon grid for expense categories (materials, transport, fuel, food, equipment, permits, maintenance, other), each cell shows icon + Arabic label from i18n capture namespace, single-tap selection with highlighted state, 44px minimum touch targets per cell, supports RTL layout. Selected category returned via onChange callback
- [X] T032 [P] [US3] Create VendorAutocomplete component in `frontend/src/features/capture/components/VendorAutocomplete.tsx`: text input with dropdown suggestions from local Dexie vendorCache table, uses useLiveQuery to reactively search by case-insensitive prefix match on name and nameAr fields, debounced input (300ms), shows Arabic name (nameAr) with English name secondary, allows free-text entry when no match (adds to cache after sync). Returns selected vendor via onChange callback. RTL-aware layout
- [X] T033 [P] [US3] Create ConfidenceBadge component in `frontend/src/features/capture/components/ConfidenceBadge.tsx`: small colored dot/badge — green (>= 0.8), amber (0.5-0.8), red (< 0.5). Positioned next to AI-filled form fields. Low-confidence fields (< 0.5) also get subtle amber border on the parent input. Accepts confidence score (0-1) as prop
- [X] T034 [P] [US3] Create vendor Pydantic schemas in `backend/app/schemas/vendor.py`: VendorResponse (id, name, name_ar, tax_registration, category_hint), VendorListResponse (vendors, total, last_updated), VendorSearchResponse (vendors)
- [X] T035 [US3] Create vendors API router in `backend/app/api/v1/vendors.py`: GET /vendors — return full vendor cache for company (for client bulk sync), supports If-Modified-Since header for incremental sync. GET /vendors/search?q={query}&limit={limit} — server-side search fallback matching name, name_ar, tax_registration. All filtered by company_id
- [X] T036 [P] [US3] Create vendor cache sync logic in `frontend/src/lib/sync.ts` (new file or extend existing): `syncVendorCache` function fetches GET /api/v1/vendors on login and every 15 minutes when online, upserts into Dexie vendorCache table via bulkPut. Call from useSyncStatus hook or app initialization
- [X] T037 [US3] Enhance ExpenseForm with polished UX in `frontend/src/features/capture/components/ExpenseForm.tsx`: replace category dropdown with CategoryGrid component, replace vendor text input with VendorAutocomplete component, add ConfidenceBadge to each AI-pre-filled field, style amount field as largest element (monospace font, tabular-nums, LTR direction, font-size 2xl+), style submit button as full-width 56px tall bottom-fixed with primary color, Arabic labels from i18n as default. Amount field uses dir="ltr" and inputMode="decimal" regardless of app RTL direction
- [X] T038 [US3] Implement auto-save and submit flow in `frontend/src/features/capture/hooks/useExpenseForm.ts`: enhance hook — auto-save to Dexie expenses table with status "draft" every 5 seconds via setInterval when form is dirty, on submit: validate required fields (amount, vendor, items), set status to "pending", add to Dexie syncQueue table, trigger Background Sync via navigator.serviceWorker. Show offline indicator when !navigator.onLine — expenses save as pending and sync later

**Checkpoint**: Expense form is polished and production-ready — category icon grid works, vendor autocomplete works offline, confidence indicators show, auto-save prevents data loss, one-tap submit queues for sync.

---

## Phase 6: User Story 4 - Combined Voice + Photo Capture (Priority: P4)

**Goal**: Field worker records voice AND photographs receipt for same expense, system merges both extractions with QR > OCR > Voice priority

**Independent Test**: Provide both a voice recording and receipt photo for same expense, verify merged form data with correct source priority

### Implementation for User Story 4

- [X] T039 [P] [US4] Create client-side merge utility in `frontend/src/lib/extraction-merge.ts`: `mergeExtractions` function accepts voice extraction and receipt extraction objects, merges fields using priority QR data > receipt OCR > voice extraction. For each field, track the source (amount_source, vendor_source, etc.). When QR detected, use QR amount and discard voice/receipt amounts. Fill gaps: if receipt provides amount but not category, and voice mentions category, use voice category. Return merged extraction object with source tracking per data-model.md combined extraction shape
- [X] T040 [US4] Create CapturePage component in `frontend/src/features/capture/pages/CapturePage.tsx`: capture mode selector with 4 options (voice, receipt, combined, manual) displayed as icon buttons, shows VoiceRecordButton + ReceiptCamera + ExpenseForm in appropriate layout per mode. For combined mode: show both VoiceRecordButton and ReceiptCamera, when both complete call mergeExtractions and pass merged result to ExpenseForm. For manual mode: show empty ExpenseForm. Uses Zustand store to manage capture state (current mode, voice blob, receipt blob, extraction results)
- [X] T041 [US4] Create capture state store in `frontend/src/features/capture/store.ts`: Zustand store managing currentCaptureMode, voiceResult (blob + extraction), receiptResult (blob + extraction), mergedExtraction. Actions: setMode, setVoiceResult, setReceiptResult, clearAll. When both voice and receipt results are present, auto-compute mergedExtraction

**Checkpoint**: Combined capture works — voice and receipt data merge correctly, QR data takes priority, gaps filled from secondary source.

---

## Phase 7: User Story 5 - Offline Capture and Background Sync (Priority: P5)

**Goal**: All capture modes work fully offline. Data saves to IndexedDB. Blobs queue for upload. Background Sync replays submissions when connectivity returns. Draft-hold workflow for voice/receipt blobs.

**Independent Test**: Enable airplane mode, create expenses via all modes, disable airplane mode, verify manual expenses auto-sync and voice/receipt drafts are flagged for AI processing and user review.

### Implementation for User Story 5

- [X] T042 [US5] Create custom service worker in `frontend/src/sw/service-worker.ts`: import Workbox modules (precacheAndRoute, cleanupOutdatedCaches from workbox-precaching; registerRoute from workbox-routing; NetworkFirst, CacheFirst from workbox-strategies; ExpirationPlugin from workbox-expiration; BackgroundSyncPlugin from workbox-background-sync). Precache app shell via self.__WB_MANIFEST. API calls: NetworkFirst with 5s timeout + 24h cache. Fonts: CacheFirst with 1yr cache. Background Sync for POST /api/v1/expenses (expense-sync-queue, 7-day retention). Background Sync for POST /api/v1/receipts/upload (receipt-upload-queue, 7-day retention). Listen for SKIP_WAITING message
- [X] T043 [P] [US5] Create useSyncStatus hook in `frontend/src/hooks/useSyncStatus.ts`: tracks isOnline (navigator.onLine + online/offline events), syncStatus (idle/syncing/offline/error), pendingCount via useLiveQuery on expenses where status="pending", queueCount via useLiveQuery on syncQueue.count. triggerSync function registers Background Sync via navigator.serviceWorker.ready + registration.sync.register("expense-sync"). Returns { isOnline, syncStatus, pendingCount, queueCount, triggerSync }
- [X] T044 [US5] Create useDraftProcessor hook in `frontend/src/features/capture/hooks/useDraftProcessor.ts`: processes offline-captured voice/receipt drafts when online — uses useLiveQuery to find expenses where status="draft" AND draftProcessed=false AND (voiceBlob!=null OR receiptBlob!=null), when navigator.onLine becomes true, process drafts LIFO (newest first): for each draft, upload voice blob to POST /api/v1/voice/extract or receipt blob to POST /api/v1/receipts/extract, store AI extraction result in expense record, set draftProcessed=true. Mark failed drafts with error status. Returns { unprocessedCount, processedDrafts }
- [X] T045 [US5] Enhance sync logic in `frontend/src/lib/sync.ts`: add blob upload queue — for pending manual expenses (no blobs), POST to /api/v1/expenses directly. For voice/receipt drafts, skip until AI-processed. Add retry with exponential backoff (1s, 2s, 4s, 8s, max 5 retries). Dedup by offline_id. Handle 409 conflict (already synced) as success. Update local expense status to "synced" and record syncedAt on success
- [X] T046 [P] [US5] Create DraftReviewBanner component in `frontend/src/features/capture/components/DraftReviewBanner.tsx`: persistent banner showing "N drafts ready for review" count (from useDraftProcessor.unprocessedCount where draftProcessed=true AND status="draft"), tap navigates to DraftReviewPage. Shows separate counts for unprocessed drafts (AI not yet run) vs ready-for-review drafts (AI processed, awaiting user confirmation). Uses i18n for Arabic text. Dismissible but reappears when new drafts are processed
- [X] T047 [US5] Create DraftReviewPage component in `frontend/src/features/capture/pages/DraftReviewPage.tsx`: lists AI-processed drafts (status="draft" AND draftProcessed=true), each item shows extracted amount, vendor, category, and confidence badges. Tap a draft to open ExpenseForm pre-filled with AI extraction for user review and confirmation. User can edit fields, then submit (changes status to "pending" and queues for sync). Options to retry failed drafts or discard. Uses useLiveQuery for reactive draft list

**Checkpoint**: Offline mode fully functional — all capture modes work without network, manual expenses auto-sync on reconnect, voice/receipt drafts are AI-processed and flagged for user review, Background Sync handles submissions even when app is closed.

---

## Phase 8: User Story 6 - Manual Expense Entry (Priority: P6)

**Goal**: Field worker enters expense manually without AI — fallback form with Arabic labels, large amount input, and vendor autocomplete

**Independent Test**: Manually enter all fields and submit, verify expense is created and queued for sync

### Implementation for User Story 6

- [X] T048 [US6] Implement manual entry flow in CapturePage in `frontend/src/features/capture/pages/CapturePage.tsx`: when manual mode is selected, render ExpenseForm with no initial data (empty form), ensure amount field is the largest element with monospace font + tabular-nums + dir="ltr" + inputMode="decimal", vendor autocomplete works from local Dexie vendorCache, category grid shows all 8 categories. No AI processing needed — direct draft → pending → sync flow
- [X] T049 [P] [US6] Handle edge case: empty vendor cache in `frontend/src/features/capture/components/VendorAutocomplete.tsx`: when vendorCache table is empty for company (new user), allow free-text vendor entry without suggestions. After successful expense sync, extract vendor name and add to vendorCache for future autocomplete. Show subtle hint text "Start typing vendor name" in Arabic

**Checkpoint**: Manual entry fully functional — form works without AI, all fields editable, vendor autocomplete works with empty cache, expense submits and syncs.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Edge case handling, error states, performance validation, and accessibility

- [X] T050 [P] Add error states for AI processing failures in `frontend/src/features/capture/components/ExpenseForm.tsx`: handle empty extraction (no data extracted from voice noise), handle 422 unreadable receipt with retake suggestion, handle 429 rate limit with Arabic "try again later" message, handle network timeout with offline fallback. All error messages in Arabic (primary) + English (secondary) via i18n
- [X] T051 [P] Add storage warning in `frontend/src/hooks/useSyncStatus.ts`: check navigator.storage.estimate() periodically, warn user when usage > 80% of quota, suggest syncing pending expenses. Show warning banner in Arabic
- [X] T052 Validate performance targets: voice extraction end-to-end < 5 seconds (verify with Egyptian 3G network simulation), receipt compression < 300KB in 95%+ cases, expense submission < 15 seconds from app open, offline sync < 30 seconds after reconnect. Add console.time measurements for development
- [X] T053 [P] Accessibility pass across all capture components in `frontend/src/features/capture/`: verify WCAG AA compliance — 44px minimum touch targets on all interactive elements (VoiceRecordButton, ReceiptCamera, CategoryGrid cells, submit button), sufficient color contrast on confidence badges (green/amber/red), aria-labels on icon-only buttons, focus management between capture modes, screen reader announcements for extraction results. Verify dark mode default renders correctly
- [X] T054 Run quickstart.md validation: verify all new dependencies install correctly, all environment variables are documented, Dexie v2 migration works with existing data, vite-plugin-pwa injectManifest builds successfully, Dockerfile includes libzbar0

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - US1 (Voice, P1): Can start after Foundational — no other story dependencies
  - US2 (Receipt, P2): Can start after Foundational — no other story dependencies
  - US3 (Form Polish, P3): Can start after Foundational — enhances form from Phase 2
  - US4 (Combined, P4): Depends on US1 + US2 completion (needs both capture modes)
  - US5 (Offline/Sync, P5): Can start after Foundational — enhances all capture modes
  - US6 (Manual, P6): Can start after US3 completion (needs polished form)
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational
    ↓
    ├── US1 (Voice) ─────────────────────┐
    ├── US2 (Receipt) ───────────────────┤
    ├── US3 (Form Polish) ───────────────┤
    └── US5 (Offline/Sync) ──────────────┤
                                         ↓
                              US4 (Combined) ← requires US1 + US2
                                         ↓
                              US6 (Manual) ← requires US3
                                         ↓
                              Phase 9: Polish
```

### Within Each User Story

- Schemas before services (backend)
- Services before API endpoints (backend)
- Hooks before components (frontend)
- Components before page integration (frontend)
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1**: T002, T003, T004, T005, T006 can all run in parallel
**Phase 2**: T008, T009, T010, T011, T014, T015, T016 can run in parallel (different files)
**US1**: T017, T018 (backend) parallel; T020, T021 (frontend) parallel
**US2**: T023, T024 (backend schemas/services) parallel; T027, T028, T029 (frontend) parallel
**US3**: T031, T032, T033, T034, T036 can all run in parallel (different files)
**US4**: T039, T041 parallel (different files)
**US5**: T043, T046 parallel (different files)
**Phase 9**: T050, T051, T053, T054 can all run in parallel

---

## Parallel Example: User Story 1

```bash
# Backend tasks in parallel:
Task T017: "Create voice extraction schemas in backend/app/schemas/voice.py"
Task T018: "Create AI voice extraction service in backend/app/services/ai_voice.py"

# Frontend tasks in parallel:
Task T020: "Create useVoiceCapture hook in frontend/src/features/capture/hooks/useVoiceCapture.ts"
Task T021: "Create VoiceRecordButton in frontend/src/features/capture/components/VoiceRecordButton.tsx"
```

## Parallel Example: User Story 2

```bash
# Backend tasks in parallel:
Task T023: "Create receipt schemas in backend/app/schemas/receipt.py"
Task T024: "Create QR decode service in backend/app/services/qr_decode.py"

# Frontend tasks in parallel:
Task T027: "Create image compression in frontend/src/lib/image-compress.ts"
Task T028: "Create useReceiptCapture hook in frontend/src/features/capture/hooks/useReceiptCapture.ts"
Task T029: "Create ReceiptCamera in frontend/src/features/capture/components/ReceiptCamera.tsx"
```

## Parallel Example: User Story 3

```bash
# All parallel (different files, no dependencies):
Task T031: "Create CategoryGrid in frontend/src/features/capture/components/CategoryGrid.tsx"
Task T032: "Create VendorAutocomplete in frontend/src/features/capture/components/VendorAutocomplete.tsx"
Task T033: "Create ConfidenceBadge in frontend/src/features/capture/components/ConfidenceBadge.tsx"
Task T034: "Create vendor schemas in backend/app/schemas/vendor.py"
Task T036: "Create vendor cache sync in frontend/src/lib/sync.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (~1 day)
2. Complete Phase 2: Foundational (~2-3 days)
3. Complete Phase 3: User Story 1 - Voice Capture (~3 days)
4. **STOP and VALIDATE**: Test voice capture independently — record Egyptian Arabic, verify form pre-fills
5. Deploy/demo: Field workers can submit expenses by voice

### Incremental Delivery

1. Setup + Foundational → Foundation ready (Days 1-4)
2. Add US1 Voice Capture → Test independently → Deploy (Days 5-7) — **MVP!**
3. Add US2 Receipt Capture → Test independently → Deploy (Days 8-10)
4. Add US3 Form Polish → Test independently → Deploy (Days 11-13)
5. Add US4 Combined Capture → Test independently → Deploy (Days 14-15)
6. Add US5 Offline/Sync → Test independently → Deploy (Days 16-18)
7. Add US6 Manual Entry → Test independently → Deploy (Days 19-20)
8. Polish Phase → Final validation → Ship (Days 21-22)
9. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (Days 1-4)
2. Once Foundational is done:
   - Developer A: US1 Voice Capture → US4 Combined
   - Developer B: US2 Receipt Capture → US5 Offline/Sync
   - Developer C: US3 Form Polish → US6 Manual Entry
3. US4 (Combined) waits for US1 + US2, then Developer A joins Polish phase
4. Stories integrate independently at each checkpoint

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The expense form (Phase 2 basic version) is a prerequisite for US1-US6
- US4 (Combined) is the only story with cross-story dependencies (needs US1 + US2)
- Service worker (US5) enhances all modes but can be developed in parallel with US1-US3
- All AI calls go through the rate limiter — test with low limits during development
- Offline drafts use a "draft-hold" workflow: blobs uploaded when online, user must confirm AI extraction

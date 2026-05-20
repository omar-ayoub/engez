# Research: Core Expense Capture

**Phase**: 0 — Outline & Research | **Date**: 2026-05-15

## Decision Records

### DR-001: Voice Recording Format

**Decision**: webm/opus via browser MediaRecorder API

**Rationale**: webm/opus is the native output format of MediaRecorder on Chrome and most Android browsers. It provides excellent compression (~16kbps for speech), keeping 60-second recordings under 200KB. OpenAI's Whisper models (including gpt-4o-mini-transcribe) natively accept webm format, so no server-side transcoding is needed.

**Alternatives considered**:
- **WAV (PCM)**: Uncompressed, 60s at 16kHz mono = ~1.9MB. Too large for offline storage and mobile upload. Rejected.
- **mp4/aac**: Requires MediaRecorder to support `audio/mp4` which is only available on Safari/iOS. Would need format detection and fallback logic. Rejected for Phase 2; may revisit if iOS audio quality issues emerge.
- **ogg/opus**: Near-identical to webm/opus in practice, but `audio/webm;codecs=opus` has broader MediaRecorder support. Rejected as redundant.

**Browser support note**: Safari/iOS supports MediaRecorder since iOS 14.3 but may output `audio/mp4` instead of `audio/webm`. The `useVoiceCapture` hook must detect the supported MIME type and pass it through to the backend. Whisper accepts both formats.

---

### DR-002: Voice AI Pipeline

**Decision**: Two-step pipeline — gpt-4o-mini-transcribe (transcription) then gpt-4o-mini (extraction)

**Rationale**: Separating transcription from extraction allows: (1) the transcription model to focus on Egyptian Arabic dialect accuracy, (2) the extraction model to receive clean text with a structured system prompt, and (3) per-company few-shot examples from the correction_feedback table to be injected into the extraction prompt (the compounding moat). The gpt-4o-mini models are chosen over gpt-4o for cost efficiency (~10x cheaper) while maintaining adequate quality for structured extraction.

**Alternatives considered**:
- **Single gpt-4o call with audio input**: GPT-4o can accept audio directly, but it doesn't support the structured JSON response format with audio input. Would also be 10x more expensive per call. Rejected.
- **Whisper API (whisper-1) + gpt-4o-mini**: The older whisper-1 model works but gpt-4o-mini-transcribe has better accuracy for Arabic dialects and lower latency. Rejected.
- **Local Whisper (whisper.cpp)**: Would eliminate API costs but requires GPU on the server and doesn't benefit from OpenAI's ongoing model improvements. Not viable for a VPS deployment. Rejected.

**Latency budget** (5-second target):
- Audio upload: ~500ms (200KB on 3G Egyptian mobile)
- Transcription: ~1.5s (gpt-4o-mini-transcribe)
- Few-shot examples DB query: ~50ms
- Extraction: ~1.5s (gpt-4o-mini with JSON mode)
- R2 upload (background, non-blocking): ~500ms
- Response transit: ~200ms
- **Total**: ~4.2s — within 5s budget

---

### DR-003: Receipt OCR Model

**Decision**: GPT-4o vision with `detail: "high"` for receipt text extraction

**Rationale**: GPT-4o vision handles Arabic text, mixed Arabic/English layouts, thermal receipt degradation, and handwritten amounts better than traditional OCR (Tesseract). The `detail: "high"` setting is critical for reading small text on receipts. Returns structured JSON with confidence scores.

**Alternatives considered**:
- **Tesseract OCR**: Free, local, but poor Arabic support, especially for thermal receipts and mixed layouts. Would require significant preprocessing. Rejected.
- **Google Cloud Vision**: Excellent Arabic support but adds a second cloud dependency (GCP) alongside OpenAI. Increases vendor lock-in and billing complexity. Rejected.
- **Azure Document Intelligence**: Strong receipt-specific model but same vendor lock-in concern. Rejected.

**Cost note**: GPT-4o vision with `detail: "high"` costs ~$0.01-0.03 per receipt image. At 200 receipts/company/day, this is ~$2-6/company/day. Acceptable for enterprise pricing.

---

### DR-004: ETA QR Code Decoding

**Decision**: pyzbar (Python libzbar wrapper) + Pillow for image preprocessing, regex for URL parsing

**Rationale**: ETA e-invoice QR codes follow a known URL format: `{portal}/receipts/search/{UUID}/share/{DateTime}#Total:{Total},IssuerRIN:{RIN}`. pyzbar handles the QR binary decoding; regex extracts the structured fields. Processing is instant (no API call), runs server-side alongside receipt OCR, and provides the highest-confidence data source.

**Alternatives considered**:
- **Client-side QR decoding (jsQR, html5-qrcode)**: Would enable offline QR decoding but adds ~50KB to the bundle and requires canvas manipulation on mobile. Since QR decoding is part of the receipt extraction API call (which requires connectivity for OCR anyway), server-side is simpler. Rejected for Phase 2.
- **ZXing (Java)**: More comprehensive barcode library but requires JVM. Not suitable for Python backend. Rejected.

**Image preprocessing for thermal receipts**: pyzbar sometimes fails on faded thermal receipts. The solution is a two-pass approach: (1) attempt decode on original image, (2) if no QR found, convert to grayscale, enhance contrast 2x with Pillow ImageEnhance, and retry.

---

### DR-005: Client-Side Image Compression

**Decision**: Canvas API with max 1200px longest edge, JPEG quality 0.85

**Rationale**: Receipt photos from modern phone cameras are typically 4000-8000px and 3-8MB. Compressing to 1200px JPEG at 0.85 quality produces images ~150-300KB that are still perfectly readable for OCR and human review. Compression happens client-side before upload, which is critical for: (1) reducing upload time on slow Egyptian mobile networks, (2) reducing R2 storage costs, (3) keeping IndexedDB blob size manageable for offline storage.

**Alternatives considered**:
- **Server-side compression**: Would require uploading the full-resolution image first (3-8MB), wasting bandwidth. Rejected.
- **WebP format**: Better compression ratio but Safari support for canvas.toBlob('image/webp') was only added in Safari 16. JPEG is universally supported. Rejected for now.
- **Lower quality (0.6-0.7)**: Risk of OCR accuracy loss on small text. 0.85 is the sweet spot. Rejected.

**Target**: 95%+ of compressed images should be under 300KB (SC-009).

---

### DR-006: Service Worker Strategy — injectManifest Migration

**Decision**: Migrate from vite-plugin-pwa `generateSW` to `injectManifest` with a custom service worker

**Rationale**: The Phase 1 service worker uses `generateSW`, which auto-generates a Workbox service worker from config. Phase 2 requires custom Background Sync logic for: (1) expense submission queue with 7-day retention, (2) receipt/voice blob upload queue, (3) separate sync tags for manual expenses vs AI-processed drafts. `injectManifest` allows writing a custom service worker that still benefits from Workbox's precaching (via `self.__WB_MANIFEST`) while adding custom sync event handlers.

**Migration impact**:
- New file: `frontend/src/sw/service-worker.ts`
- vite.config.ts: change `strategies` from default to `"injectManifest"`, add `srcDir` and `filename`
- Existing runtime caching config moves into the custom service worker code
- Precaching continues to work via Workbox's `precacheAndRoute(self.__WB_MANIFEST)`

**Alternatives considered**:
- **Stay with generateSW + Workbox BackgroundSyncPlugin in config**: Workbox's BackgroundSyncPlugin can be configured declaratively, but it doesn't support the draft-hold workflow where blob upload and AI processing are separate steps. Rejected.
- **Custom service worker without Workbox**: Lose precaching and cache strategy helpers. Too much boilerplate. Rejected.

---

### DR-007: Blob Storage — Cloudflare R2

**Decision**: Cloudflare R2 via boto3 (S3-compatible API), signed URLs for access

**Rationale**: R2 is already in the constitution's tech stack. The boto3 SDK provides S3-compatible access. Upload flow: backend receives blob from client -> uploads to R2 -> returns signed URL. Signed URLs have configurable expiry (default 1 hour for viewing, 15 minutes for upload). No egress fees with R2 (unlike S3).

**Upload approach**: All uploads go through the FastAPI backend (not presigned PUT URLs from the client). This ensures: (1) authentication is validated, (2) file size/type is checked server-side, (3) the R2 key path includes company_id for tenant isolation, (4) no R2 credentials are exposed to the client.

**R2 key structure**: `{company_id}/{type}/{YYYY-MM}/{uuid}.{ext}`
- Example: `comp-123/voice/2026-05/abc-def.webm`
- Example: `comp-123/receipts/2026-05/ghi-jkl.jpg`

**Alternatives considered**:
- **Presigned upload URLs**: Client uploads directly to R2 via presigned URL. Faster for large files but requires exposing R2 credentials or a presign endpoint. Adds complexity. Rejected for Phase 2.
- **Local filesystem storage**: Not viable for production VPS with limited disk. Rejected.

---

### DR-008: AI Call Rate Limiting

**Decision**: Redis sliding window rate limiter, keyed by company_id, with configurable limits

**Rationale**: OpenAI API calls are the primary cost driver. Rate limiting prevents: (1) runaway costs from bugs or abuse, (2) hitting OpenAI's own rate limits, (3) one tenant monopolizing shared API quota. Redis is already in the stack for Phase 1 (session cache).

**Default limits**:
- Voice extraction: 100 calls/company/hour
- Receipt extraction: 100 calls/company/hour
- Combined (voice+receipt): counts against both limits

**Implementation**: Redis `INCR` + `EXPIRE` on key `ratelimit:{company_id}:{endpoint}:{window}`. Sliding window approximation using two adjacent fixed windows.

**Alternatives considered**:
- **In-memory rate limiting**: Lost on server restart. Not suitable. Rejected.
- **Per-user rate limiting**: Too granular — a company with 50 field workers would need high per-user limits that defeat the purpose. Company-level is the right granularity. Rejected.
- **Token bucket**: More complex to implement, marginal benefit over sliding window for this use case. Rejected.

---

### DR-009: Draft Notification Strategy

**Decision**: In-app banner notification (DraftReviewBanner component), not push notification

**Rationale**: When offline-captured drafts are AI-processed and ready for review, the user sees a banner on the home screen: "N drafts ready for review". This is simpler than push notifications (which require VAPID setup, notification permissions, and service worker message handling). Push notifications are planned for Phase 4 (alerts/approvals).

**User flow**: Home screen shows DraftReviewBanner with count of drafts where `status="draft"` AND `aiExtraction != null`. Tapping the banner navigates to DraftReviewPage.

**Alternatives considered**:
- **Push notification**: Requires notification permission (users may decline), VAPID key setup, and SW push event handler. Overkill for Phase 2. Deferred to Phase 4. Rejected.
- **Toast/snackbar on reconnect**: Transient — user may miss it. Rejected.

---

### DR-010: Offline Draft Processing Flow

**Decision**: Client-initiated processing on reconnect, not server-push

**Rationale**: When the device reconnects, the client (not the server) initiates blob upload and AI processing for offline drafts. Flow: (1) `useDraftProcessor` hook detects online + drafts with unprocessed blobs, (2) for each draft, uploads blob to the extract endpoint, (3) receives AI extraction, (4) updates local expense in Dexie, (5) shows banner notification.

This is simpler than a server-push architecture (which would require WebSocket or SSE for the server to notify the client that processing is done). The client already knows which drafts need processing (it stored them locally).

**Processing order**: Newest drafts first (LIFO) — the most recent expense is most likely the one the user wants to review first.

**Error handling**: If AI processing fails for a draft (corrupted audio, unreadable image), the draft is marked with an error status and the user can retry, manually fill, or discard.

**Alternatives considered**:
- **Server-initiated processing**: Client uploads blob, server processes asynchronously, notifies client via WebSocket/SSE when done. More complex, requires persistent connection. Rejected.
- **Background Sync for blob processing**: The Background Sync API is for fire-and-forget network requests. It doesn't support receiving and storing responses in IndexedDB. Rejected for AI processing (used only for expense submission).

---

### DR-011: Vendor Autocomplete — Local-First Search

**Decision**: Dexie.js local query with case-insensitive prefix matching on Arabic and English names

**Rationale**: Vendor autocomplete must work offline. The vendor cache is synced from the server when online and stored in a Dexie `vendorCache` table. Search is a simple `startsWith` query on the `name` and `nameAr` fields. For a typical company with <1000 vendors, this is instant.

**Cache sync strategy**: On login and periodically (every 15 minutes when online), fetch the full vendor list for the company. Dexie `bulkPut` upserts the local cache. This is acceptable because vendor lists are small (<1000 entries, <100KB).

**Alternatives considered**:
- **Server-side search with network fallback**: Would fail offline. Rejected.
- **Fuse.js fuzzy search**: Adds ~20KB to the bundle. Simple prefix matching is sufficient for vendor names. Can add later if users report issues. Rejected for Phase 2.

---

### DR-012: Expense Form Architecture

**Decision**: React Hook Form 7 with Zustand for cross-component state, Dexie auto-save every 5 seconds

**Rationale**: React Hook Form is already in the tech stack (Phase 1) and provides excellent performance for forms with many fields. Zustand manages the capture state (current mode, voice blob, receipt blob, AI extraction results) that needs to be shared between the capture components and the form. Auto-save uses a `setInterval` that calls `db.expenses.put(currentDraft)` every 5 seconds when the form is dirty.

**Form field layout** (mobile-first, single column):
1. Amount (large, monospace, LTR) — always visible at top
2. Vendor (autocomplete) — required
3. Items/description (text input) — required
4. Category (2x4 icon grid) — optional, below fold
5. Project (recent projects chips) — optional
6. Date (defaults to today) — optional
7. Notes (expandable textarea) — optional
8. Submit button (full-width, 56px, fixed bottom)

**Confidence highlighting**: Fields pre-filled by AI show a ConfidenceBadge (green >= 0.8, amber 0.5-0.8, red < 0.5). Low-confidence fields (<0.5) get a subtle amber border to draw attention.

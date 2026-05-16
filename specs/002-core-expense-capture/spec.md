# Feature Specification: Core Expense Capture

**Feature Branch**: `002-core-expense-capture`

**Created**: 2026-05-15

**Status**: Clarified

**Input**: User description: "Build the core expense capture features that replace the WhatsApp + Spreadsheet workflow for Egyptian field workers. Four capture modes: voice, receipt photo, combined, and manual. All modes work fully offline with automatic sync."

## Clarifications

### Session 2026-05-15

- Q: What is the AI voice processing latency target (from recording end to pre-filled form)? → A: 5 seconds (relaxed from initial 2s target for Egyptian mobile network realism)
- Q: When voice/receipt blobs are captured offline, what happens when connectivity returns? → A: Expense stays as "draft" until AI processes the blob online; user must revisit the draft and confirm/submit after AI pre-fills the form
- Q: Which fields are required to submit an expense? → A: Amount, vendor, and items (what was purchased) are required. Category, project, date, and notes are optional.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Voice Expense Capture (Priority: P1)

A field worker on a construction site has just paid a cement supplier in cash. Instead of typing, they tap one button, speak in Egyptian Arabic dialect ("دفعت ألف وخمسمية جنيه لمحل الأسمنت في موقع المعادي"), and the system transcribes the speech, extracts structured expense data (amount, currency, category, vendor, project), and pre-fills the expense form — ready for a single-tap submit.

**Why this priority**: Voice capture is the primary differentiator that makes this app faster than WhatsApp. Field workers have dirty or gloved hands, are in noisy environments, and need to submit expenses in under 15 seconds. Voice eliminates typing entirely.

**Independent Test**: Can be fully tested by recording a voice clip in Egyptian Arabic dialect and verifying the form auto-fills with correct amount, category, and vendor. Delivers immediate value — a complete expense submission flow.

**Acceptance Scenarios**:

1. **Given** a logged-in field worker on the capture screen, **When** they tap the record button and speak an expense description in Egyptian Arabic, **Then** the system displays a transcription and pre-fills the expense form with extracted amount, currency, category, vendor, and project hint within 5 seconds of recording end.
2. **Given** a voice recording has been processed, **When** the AI extraction has low confidence on a specific field (e.g., amount), **Then** that field is visually highlighted so the user knows to verify it.
3. **Given** a voice recording, **When** the recording exceeds the maximum allowed duration, **Then** recording stops automatically and the captured audio is still processed.
4. **Given** a field worker has previously corrected AI extractions for their company, **When** a new voice recording is processed, **Then** the system uses historical correction patterns to improve extraction accuracy for that company.

---

### User Story 2 - Receipt Photo Capture with QR Decode (Priority: P2)

A field worker photographs a receipt after a purchase. The system extracts text from the receipt image (Arabic and English) using AI vision. If the receipt contains an ETA-compliant e-invoice QR code, the system decodes it to auto-fill the vendor tax registration number, total amount, date, and invoice UUID — achieving zero-typing submission for compliant receipts.

**Why this priority**: Receipt photos provide auditable proof of expense. The ETA QR decode is a unique capability unavailable in competing Egyptian expense tools, and it provides verified, tamper-proof data that accountants trust over manual entry.

**Independent Test**: Can be tested by photographing an Arabic thermal receipt (with and without ETA QR code) and verifying form fields populate correctly. ETA QR data should override OCR data for amount and vendor tax ID.

**Acceptance Scenarios**:

1. **Given** a logged-in field worker, **When** they photograph a receipt, **Then** the image is compressed before processing and the system extracts amount, vendor, date, category, and line items from the receipt.
2. **Given** a receipt image with an ETA-compliant QR code, **When** the image is processed, **Then** the QR data (amount, vendor tax registration, invoice UUID, date) is decoded and takes precedence over AI-extracted values for those fields.
3. **Given** a faded thermal receipt or low-light photo, **When** the image is processed, **Then** the system enhances the image and still attempts extraction, reporting confidence scores for each field.
4. **Given** a receipt with a QR-decoded vendor tax registration number, **When** a vendor with that tax number exists in the company's vendor cache, **Then** the vendor name and default category are auto-filled from the cache.

---

### User Story 3 - Expense Form and Submission (Priority: P3)

After any capture mode (voice, receipt, combined, or manual), the field worker sees a pre-filled expense form. The form is optimized for one-handed use on mobile: the amount is the largest element, category selection uses a visual icon grid (not a dropdown), vendor uses autocomplete, and project is selected from a recent-projects list. The submit button is full-width and tall for easy thumb tapping. The entire flow from app open to expense submitted takes under 15 seconds.

**Why this priority**: The form is the convergence point for all capture modes. Without a fast, well-designed form, even perfect AI extraction would fail at the last mile. The form's speed and ease of use directly determine whether field workers adopt the app or revert to WhatsApp.

**Independent Test**: Can be tested by manually entering an expense (no AI) and verifying the form saves, submits, and queues for sync. Delivers standalone value as a manual expense entry tool.

**Acceptance Scenarios**:

1. **Given** pre-filled data from voice or receipt capture, **When** the expense form loads, **Then** all extracted fields are populated, with low-confidence fields visually highlighted.
2. **Given** a field worker is filling the form, **When** they have not submitted after 5 seconds of inactivity, **Then** the form auto-saves as a draft locally.
3. **Given** a completed expense form, **When** the field worker taps the submit button, **Then** the expense is saved with "pending" status and queued for server sync.
4. **Given** the vendor field, **When** the field worker starts typing, **Then** autocomplete suggestions appear from the company's cached vendor database.
5. **Given** the category field, **When** the field worker views category options, **Then** categories are displayed as a visual icon grid with Arabic labels, not a text dropdown.

---

### User Story 4 - Combined Voice + Photo Capture (Priority: P4)

A field worker records a voice note while also photographing the receipt for the same expense. The system processes both inputs and merges the extracted data intelligently: QR-decoded data takes highest priority, then receipt OCR data, then voice-extracted data. The merged result pre-fills the form with the most reliable values.

**Why this priority**: Combined mode provides the highest accuracy by cross-referencing two data sources. It is valuable but depends on both voice (P1) and receipt (P2) being functional first.

**Independent Test**: Can be tested by providing both a voice recording and a receipt photo for the same expense, then verifying the form merges data correctly with QR > OCR > Voice priority.

**Acceptance Scenarios**:

1. **Given** a field worker has both a voice recording and a receipt photo for the same expense, **When** both are processed, **Then** the form is pre-filled with merged data using the priority: QR data > receipt OCR > voice extraction.
2. **Given** conflicting amounts between voice and receipt, **When** the receipt has an ETA QR code, **Then** the QR amount is used and the voice amount is discarded.
3. **Given** the receipt provides amount and vendor but not category, **When** the voice recording mentions a category, **Then** the category from voice is used to fill the gap.

---

### User Story 5 - Offline Capture and Background Sync (Priority: P5)

A field worker is on a remote construction site with no cellular signal. They can still open the app, capture expenses via any mode (voice, photo, manual), save them locally, and continue working. When connectivity returns (hours or days later), all pending expenses sync automatically in the background — even if the app is closed. No data is ever lost due to network conditions.

For voice and receipt captures made offline, the raw blobs (audio, images) are stored locally. When connectivity returns, the system uploads the blobs for AI processing. The expense remains as a "draft" until AI processing completes and the user revisits to review the AI-extracted data and confirm submission. The system notifies the user that drafts are ready for review.

**Why this priority**: Offline capability is a constitutional requirement (Principle I). Egyptian field sites frequently lose connectivity. Without offline mode, the app would be unusable for the primary audience. However, it's P5 because it enhances all other stories rather than standing alone.

**Independent Test**: Can be tested by enabling airplane mode, creating multiple expenses, then disabling airplane mode and verifying all expenses sync to the server without user intervention (manual-only expenses) and that voice/receipt drafts are flagged for user review after AI processing.

**Acceptance Scenarios**:

1. **Given** the device has no network connectivity, **When** a field worker opens the app, **Then** the app loads from cache and all UI is fully functional.
2. **Given** no connectivity, **When** a field worker captures a manual expense (no voice/receipt) and taps submit, **Then** the expense is saved locally with "pending" status and syncs automatically when online.
3. **Given** no connectivity, **When** a field worker captures a voice or receipt expense, **Then** the expense is saved locally as a "draft" with the raw blob stored for deferred AI processing.
4. **Given** offline-captured voice/receipt drafts, **When** connectivity returns, **Then** the system uploads the blobs, runs AI processing, and notifies the user that drafts are ready for review.
5. **Given** an AI-processed draft, **When** the user revisits the draft, **Then** the form is pre-filled with AI-extracted data and the user must confirm before the expense is submitted.
6. **Given** pending unsynced expenses (manual), **When** network connectivity is restored, **Then** all pending expenses are synced to the server automatically without user action.
7. **Given** a sync attempt fails mid-way, **When** connectivity returns again, **Then** the system retries failed items with increasing delays, without duplicating already-synced items.
8. **Given** the app is closed and has pending manual expenses, **When** connectivity is restored in the background, **Then** the system syncs pending expenses without requiring the app to be open.
9. **Given** a visual indicator, **When** there are unsynced expenses or unreviewed AI-processed drafts, **Then** the indicator shows both counts separately so the user knows action is needed.

---

### User Story 6 - Manual Expense Entry (Priority: P6)

A field worker needs to enter an expense without voice or photo — perhaps a cash tip to a porter, or a small purchase with no receipt. They open the form, type the amount (large, monospace, LTR input), select a category from the icon grid, optionally pick a vendor from autocomplete, choose a project, and submit. Arabic labels are the default, with English available via a settings toggle.

**Why this priority**: Manual entry is the fallback when AI capture isn't possible. It's the simplest mode and serves as the baseline experience. It's P6 because voice and receipt capture are the core differentiators.

**Independent Test**: Can be tested by manually entering all fields and submitting, verifying the expense is created and queued for sync.

**Acceptance Scenarios**:

1. **Given** a field worker on the expense form with no pre-filled data, **When** they tap the amount field, **Then** a large, monospace, left-to-right numeric input is displayed regardless of the app's RTL direction.
2. **Given** the manual entry form, **When** the field worker completes all required fields and taps submit, **Then** the expense is saved and queued for server sync.

---

### Edge Cases

- What happens when a voice recording contains no discernible expense information (e.g., background noise only)? The system should return an empty form with a message indicating no data could be extracted.
- What happens when a receipt photo is completely unreadable (e.g., blurry, too dark)? The system should show a low-confidence warning and suggest retaking the photo, while still allowing manual entry.
- What happens when the device runs out of local storage? The system should warn the user before storage is exhausted and suggest syncing pending expenses.
- What happens when two expenses are submitted for the exact same amount, vendor, and date? The system should accept both — duplicate detection is an accountant-side concern (Phase 3).
- What happens when the vendor cache is empty (new company, first use)? The autocomplete field should allow free-text entry; typed vendor names are added to the cache after successful sync.
- What happens when the voice recording captures multiple expenses in one clip? The system should extract the first/primary expense and note any additional mentions in a "notes" field.
- What happens during very long offline periods (7+ days)? Pending items should be retained for at least 7 days; beyond that, the system should warn about potential data staleness.
- What happens when an offline-captured draft's AI processing fails (e.g., corrupted audio, unprocessable image)? The system should notify the user and allow them to either retry, manually fill the form, or discard the draft.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a voice recording capability that captures audio optimized for speech recognition (noise-suppressed, echo-cancelled).
- **FR-002**: System MUST transcribe Egyptian Arabic dialect speech and extract structured expense fields: amount, currency, items/description, category, vendor, and project hint.
- **FR-003**: System MUST return confidence scores (0–1) for each AI-extracted field so the UI can highlight uncertain values.
- **FR-004**: System MUST incorporate per-company correction history into AI extraction prompts, improving accuracy over time.
- **FR-005**: System MUST accept receipt photographs and extract text from Arabic and English receipts, including faded thermal paper.
- **FR-006**: System MUST decode ETA-compliant e-invoice QR codes from receipt images, extracting invoice UUID, total amount, vendor tax registration number, and date.
- **FR-007**: When QR data is available, system MUST prefer QR-decoded values over AI-extracted values for amount, vendor tax ID, and date.
- **FR-008**: System MUST compress receipt images before upload to reduce file size while maintaining readability.
- **FR-009**: System MUST merge extraction results from voice and receipt sources when both are provided, using the priority: QR data > receipt OCR > voice extraction.
- **FR-010**: System MUST provide an expense form that accepts pre-filled data from any capture mode and allows user editing before submission. Required fields for submission: amount, vendor, and items (description of what was purchased). Category, project, date, and notes are optional.
- **FR-011**: System MUST display expense categories as a visual icon grid, not a text dropdown.
- **FR-012**: System MUST provide vendor autocomplete from a locally cached vendor database, scoped to the user's company.
- **FR-013**: System MUST auto-save expense drafts locally at regular intervals (every 5 seconds) to prevent data loss.
- **FR-014**: System MUST submit expenses to a local queue and sync them to the server when connectivity is available.
- **FR-015**: System MUST support background sync — pending manual expenses sync automatically when connectivity returns, even if the app is not in the foreground.
- **FR-016**: System MUST retain unsynced expenses locally for at least 7 days.
- **FR-017**: System MUST display the count of pending/unsynced expenses and unreviewed AI-processed drafts to the user at all times.
- **FR-018**: System MUST enforce a maximum voice recording duration (60 seconds) with auto-stop.
- **FR-019**: System MUST enforce a maximum receipt image upload size (10 MB raw, compressed to target under 300 KB).
- **FR-020**: System MUST support vendor cache lookup by tax registration number when QR-decoded vendor data is available.
- **FR-021**: System MUST present amount fields in left-to-right direction with monospace, tabular-number formatting regardless of document direction.
- **FR-022**: System MUST scope all expense data, vendor caches, and correction history to the authenticated user's company (multi-tenant isolation).
- **FR-023**: System MUST rate-limit AI processing calls to prevent cost overruns.
- **FR-024**: System MUST complete AI voice processing (transcription + extraction) and return pre-filled form data within 5 seconds of recording end, under normal network conditions.
- **FR-025**: When voice or receipt blobs are captured offline, the system MUST store them locally as drafts, upload them for AI processing when connectivity returns, and require the user to review and confirm the AI-extracted data before submission.
- **FR-026**: System MUST notify the user when offline-captured drafts have been AI-processed and are ready for review.

### Key Entities

- **Expense**: A financial record with amount (required), vendor (required), items/description (required), currency, category, project, date, notes, status (draft/pending/synced/failed), capture mode (voice/receipt/combined/manual), and optional linked voice recording and receipt image. Expenses captured offline with voice/receipt blobs remain in "draft" status until AI processing completes and the user confirms.
- **Voice Recording**: An audio blob captured by the field worker, linked to an expense, with transcription text and extraction metadata.
- **Receipt Image**: A compressed photograph of a receipt, linked to an expense, with OCR extraction metadata and optional ETA QR data.
- **Vendor Cache**: A company-scoped cache of known vendors with name, tax registration number, and default category hint. Populated from synced expenses and QR decodes.
- **Correction Feedback**: A record of user corrections to AI-extracted fields, scoped by company, used to improve future extraction accuracy (the compounding moat).
- **Sync Queue**: A local queue of pending operations (expense submissions, file uploads, deferred AI processing requests) waiting for connectivity.
- **Category**: A predefined set of expense categories (materials, transport, fuel, food, equipment, permits, maintenance, other) with icons and Arabic/English labels.
- **Project**: An active project belonging to a company, with Arabic and English names, used for expense attribution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Field workers can complete the full flow from app open to expense submitted in under 15 seconds using voice capture.
- **SC-002**: AI voice extraction correctly identifies the expense amount in at least 90% of clear Egyptian Arabic recordings.
- **SC-003**: ETA QR codes are decoded successfully from at least 95% of receipt photos containing compliant QR codes.
- **SC-004**: Receipt OCR extracts a usable amount from at least 85% of readable receipt photos (including Arabic thermal receipts).
- **SC-005**: All four capture modes (voice, receipt, combined, manual) function fully without network connectivity.
- **SC-006**: Pending manual expenses sync automatically within 30 seconds of connectivity being restored.
- **SC-007**: Zero data loss occurs during offline usage periods of up to 7 days.
- **SC-008**: Per-company AI accuracy improves measurably after 50+ correction feedback entries (the compounding moat effect).
- **SC-009**: Receipt images are compressed to under 300 KB in at least 95% of cases without making text unreadable.
- **SC-010**: The expense form auto-save prevents data loss for 100% of in-progress entries when the app is interrupted (backgrounded, closed, or crashes).
- **SC-011**: AI voice processing (transcription + field extraction) completes within 5 seconds of recording end under normal network conditions.
- **SC-012**: Offline-captured voice/receipt drafts are AI-processed and available for user review within 60 seconds of connectivity being restored.

## Assumptions

- Field workers have smartphones with camera and microphone access (Android 10+ or iOS 15+).
- The primary language of voice input is Egyptian Arabic dialect; formal Modern Standard Arabic and English inputs are secondary.
- ETA e-invoice QR codes follow the documented Egyptian Tax Authority format with UUID, total, issuer RIN, and datetime in the URL structure.
- The vendor cache starts empty for new companies and is built organically from synced expenses and QR decodes.
- Categories are predefined and fixed (materials, transport, fuel, food, equipment, permits, maintenance, other); custom categories are out of scope for this phase.
- Currency defaults to EGP unless explicitly stated in voice or receipt; multi-currency support is limited to extraction (no real-time conversion).
- The Phase 1 authentication system, database schema, and app shell are already implemented and available as the foundation.
- Correction feedback is collected in Phase 3 (Review Desk) but the extraction pipeline must be designed to consume it from this phase onward.
- Background sync depends on browser support; a polling fallback is needed for browsers that lack the Background Sync API (notably Safari/iOS).
- AI processing (transcription and OCR) requires network connectivity; offline-captured voice/receipt blobs are stored locally as drafts and processed when connectivity returns. The user must review and confirm AI-extracted data before submission.

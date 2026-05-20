# Tasks: Accountant Review Desk

**Input**: Design documents from `/specs/003-review-desk/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Test tasks are included because the feature specification defines independent tests for each user story and quickstart.md requires backend and Playwright coverage.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently after the shared foundation is complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or depends only on completed setup/foundation work
- **[Story]**: User story label for traceability, used only inside user-story phases
- Every task includes a concrete file path

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add dependency, environment, and file structure prerequisites used by later phases.

- [x] T001 Add `pywebpush>=2,<3` to backend dependencies and refresh the lockfile in backend/pyproject.toml and backend/uv.lock
- [x] T002 Add documented VAPID, Redis, and R2 review desk environment variables to .env.example
- [x] T003 [P] Create backend review module placeholders in backend/app/api/v1/review.py, backend/app/api/v1/notifications.py, backend/app/schemas/review.py, backend/app/schemas/notification.py, backend/app/services/review_queue.py, backend/app/services/review_actions.py, backend/app/services/audit_log.py, and backend/app/services/push_notifications.py
- [x] T004 [P] Create frontend review feature folders and placeholder type module in frontend/src/features/review/pages/, frontend/src/features/review/components/, frontend/src/features/review/hooks/, and frontend/src/features/review/review-types.ts
- [x] T005 [P] Create Arabic and English review locale files in frontend/src/locales/ar/review.json and frontend/src/locales/en/review.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core schema, authorization, routing, offline storage, and shared services required before user-story work starts.

**CRITICAL**: No user story work should begin until this phase is complete.

- [x] T006 [P] Add `review_version`, `reviewed_by`, `reviewed_at`, and review queue indexes to the Expense model in backend/app/models/expense.py
- [x] T007 [P] Add ReviewAuditLog model with append-only fields and indexes in backend/app/models/review_audit_log.py
- [x] T008 Export ReviewAuditLog from backend/app/models/__init__.py
- [x] T009 [P] Add correction feedback metrics and expense lookup indexes to backend/app/models/correction.py
- [x] T010 Create Alembic migration for expense review columns, queue indexes, correction indexes, review_audit_logs, and PostgreSQL immutability trigger in backend/alembic/versions/003_review_desk.py
- [x] T011 Add accountant/admin authorization dependency and tenant role helpers in backend/app/core/deps.py
- [x] T012 [P] Define shared review enums, pagination schemas, conflict error schemas, and audit log response schemas in backend/app/schemas/review.py
- [x] T013 [P] Define push subscription request/response schemas in backend/app/schemas/notification.py
- [x] T014 Register review and notification routers in backend/app/api/v1/__init__.py
- [x] T015 [P] Add receipt signed URL refresh helper for review detail retry flow in backend/app/services/r2_storage.py
- [x] T016 [P] Add ReviewQueueCache, ReviewDetailCache, ReviewActionOutboxItem interfaces and Dexie version 3 stores in frontend/src/lib/db.ts
- [x] T017 Implement review action outbox draining and retry/conflict state handling in frontend/src/lib/review-sync.ts
- [x] T018 Wire review outbox draining into the existing sync lifecycle in frontend/src/lib/sync.ts
- [x] T019 Add review i18n namespace imports and resources in frontend/src/lib/i18n.ts
- [x] T020 [P] Define frontend review API DTOs and state types in frontend/src/features/review/review-types.ts

**Checkpoint**: Foundation ready - user story implementation can now proceed in priority order or in parallel by separate owners.

---

## Phase 3: User Story 1 - Expense Review Queue (Priority: P1) MVP

**Goal**: Accountants can open a tenant-scoped queue, view paginated expense summaries, filter by project/date/employee/status/amount, sort by date/amount/project, and receive 30-second polling updates.

**Independent Test**: Seed pending and non-pending expenses across tenants, then verify `/review` renders the correct rows, filters/sorts correctly, paginates, handles empty states, and keeps Arabic RTL layout.

### Tests for User Story 1

- [x] T021 [P] [US1] Add backend queue contract tests for role access, tenant isolation, pagination, filters, sorting, confidence summary, anomaly count, and bulk eligibility in backend/tests/test_review_queue.py
- [ ] T022 [P] [US1] Add Playwright tests for `/review` RTL rendering, filters, sort controls, pagination/empty states, and cached offline queue state in frontend/e2e/review-desk.spec.ts

### Implementation for User Story 1

- [x] T023 [US1] Add ReviewQueueItem and ReviewQueueResponse schemas in backend/app/schemas/review.py
- [x] T024 [US1] Implement server-side queue filtering, sorting, pagination, confidence summary, anomaly count, and bulk eligibility query logic in backend/app/services/review_queue.py
- [x] T025 [US1] Implement `GET /api/v1/expenses/queue` with accountant/admin authorization and tenant scoping in backend/app/api/v1/review.py
- [x] T026 [P] [US1] Implement review queue API client helpers in frontend/src/features/review/review-api.ts
- [x] T027 [US1] Implement `useReviewQueue` with URL query params, 30-second visible-tab polling, manual refresh, cache writes, and offline cache fallback in frontend/src/features/review/hooks/useReviewQueue.ts
- [x] T028 [P] [US1] Implement project/date/employee/status/amount/sort controls in frontend/src/features/review/components/ReviewFilters.tsx
- [x] T029 [P] [US1] Implement queue rows, confidence summary, capture mode icons, ETA badge, anomaly labels, amount LTR formatting, and pagination controls in frontend/src/features/review/components/ReviewQueueList.tsx
- [x] T030 [US1] Implement accountant queue page composition, loading states, empty states, offline state, and pending outbox indicators in frontend/src/features/review/pages/ReviewQueuePage.tsx
- [x] T031 [US1] Add protected `/review` route and accountant/admin access handling in frontend/src/App.tsx
- [x] T032 [US1] Add queue labels, filter labels, empty states, conflict/offline messages, and accessibility text in frontend/src/locales/ar/review.json and frontend/src/locales/en/review.json

**Checkpoint**: User Story 1 works independently as a usable queue MVP.

---

## Phase 4: User Story 2 - Expense Detail Review (Priority: P2)

**Goal**: Accountants can open one expense and inspect the receipt, AI fields with confidence indicators, voice transcript, ETA badge, anomaly flags, and audit history.

**Independent Test**: Open a seeded expense with receipt, voice transcript, ETA data, confidence values, and anomalies, then verify all evidence sections render and receipt URL refresh works on image failure.

### Tests for User Story 2

- [x] T033 [P] [US2] Add backend detail and signed receipt URL refresh tests for tenant scope, accountant/admin access, audit history, and missing receipt behavior in backend/tests/test_review_actions.py
- [ ] T034 [P] [US2] Add Playwright tests for `/review/:expenseId` receipt zoom, confidence badges, transcript, ETA badge, anomaly labels, audit timeline, and manual-entry no-receipt layout in frontend/e2e/review-desk.spec.ts

### Implementation for User Story 2

- [x] T035 [US2] Add ReviewDetailResponse, ReceiptUrlResponse, confidence, ETA, anomaly, employee, and audit history schemas in backend/app/schemas/review.py
- [x] T036 [US2] Implement detail evidence and audit history query helpers in backend/app/services/review_queue.py
- [x] T037 [US2] Implement `GET /api/v1/expenses/{expense_id}/review-detail` and `POST /api/v1/expenses/{expense_id}/receipt-url` in backend/app/api/v1/review.py
- [x] T038 [P] [US2] Implement `useReviewDetail` with detail cache writes, offline fallback, 409 refresh support, and receipt URL retry handling in frontend/src/features/review/hooks/useReviewDetail.ts
- [x] T039 [P] [US2] Implement zoom, pan, double-tap zoom, load failure retry, and reduced-motion behavior in frontend/src/features/review/components/ReceiptZoomViewer.tsx
- [x] T040 [P] [US2] Implement AI field evidence, transcript, ETA badge, anomaly flags, and manual-entry adaptive layout in frontend/src/features/review/components/ExpenseEvidencePanel.tsx
- [x] T041 [P] [US2] Implement three-tier confidence indicator with icon/text labels in frontend/src/features/review/components/ConfidenceBadge.tsx
- [x] T042 [P] [US2] Implement immutable review history display in frontend/src/features/review/components/AuditTimeline.tsx
- [x] T043 [US2] Implement detail page layout, loading/error states, receipt fallback, and back-to-queue navigation in frontend/src/features/review/pages/ReviewDetailPage.tsx
- [x] T044 [US2] Add protected `/review/:expenseId` route and accountant/admin access handling in frontend/src/App.tsx
- [x] T045 [US2] Add detail evidence, receipt, ETA, anomaly, confidence, and audit timeline strings in frontend/src/locales/ar/review.json and frontend/src/locales/en/review.json

**Checkpoint**: User Story 2 works independently for evidence review without approve/reject actions.

---

## Phase 5: User Story 3 - Approve and Reject Actions (Priority: P3)

**Goal**: Accountants can approve with one tap, reject with a required reason, preserve audit history, handle stale conflicts, navigate to the next pending expense, and allow rejected expenses to be resubmitted on the same record.

**Independent Test**: Approve and reject seeded pending expenses, verify status changes, audit rows, rejection reason validation, conflict responses, next-pending navigation, and field-worker decision notification enqueue behavior.

### Tests for User Story 3

- [x] T046 [P] [US3] Add backend tests for approve, reject, rejection validation, optimistic conflicts, immutable audit rows, tenant isolation, next pending ID, and resubmit transition in backend/tests/test_review_actions.py
- [ ] T047 [P] [US3] Add Playwright tests for approve, reject reason dialog, disabled reject confirmation, pending outbox state, stale conflict refresh, and next-expense navigation in frontend/e2e/review-desk.spec.ts

### Implementation for User Story 3

- [x] T048 [US3] Implement append-only audit creation helpers for status changes and resubmits in backend/app/services/audit_log.py
- [x] T049 [US3] Implement approve, reject, and resubmit transactional service functions with `review_version` checks, tenant scope, status guards, review metadata, and audit insert in backend/app/services/review_actions.py
- [x] T050 [US3] Implement field-worker decision notification enqueue calls after committed approve, reject, and resubmit-side effects in backend/app/services/push_notifications.py
- [x] T051 [US3] Implement approve and reject endpoints in backend/app/api/v1/review.py
- [x] T052 [US3] Implement rejected-expense resubmit endpoint for original field worker/admin in backend/app/api/v1/expenses.py
- [x] T053 [P] [US3] Implement reject reason dialog with minimum length validation and accessible focus handling in frontend/src/features/review/components/RejectReasonDialog.tsx
- [x] T054 [US3] Implement approve/reject outbox-first actions, immediate sync, conflict marking, and next-pending response handling in frontend/src/features/review/hooks/useReviewActions.ts
- [x] T055 [US3] Wire approve/reject buttons, pending confirmation state, conflict refresh, and post-action navigation into frontend/src/features/review/pages/ReviewDetailPage.tsx
- [x] T056 [US3] Add approve, reject, resubmit, pending confirmation, conflict, and validation strings in frontend/src/locales/ar/review.json and frontend/src/locales/en/review.json

**Checkpoint**: User Story 3 provides the core auditable decision workflow.

---

## Phase 6: User Story 4 - Inline Field Correction (Priority: P4)

**Goal**: Accountants can edit AI-extracted fields inline, update the expense, store correction feedback only for AI-origin values, audit every correction, and feed tenant-specific correction examples into future extraction.

**Independent Test**: Correct AI and manual-entry fields, then verify expense values, correction_feedback creation rules, audit rows, review_version increments, and few-shot example retrieval by company.

### Tests for User Story 4

- [x] T057 [P] [US4] Add backend tests for correct endpoint validation, allowed fields, AI-origin feedback creation, manual-entry no-feedback behavior, audit rows, conflicts, and tenant isolation in backend/tests/test_review_actions.py
- [x] T058 [P] [US4] Add backend tests for tenant-scoped correction feedback examples used by extraction prompts in backend/tests/test_ai_metrics.py
- [ ] T059 [P] [US4] Add Playwright tests for inline field editing, pending outbox state, correction confirmation, and conflict display in frontend/e2e/review-desk.spec.ts

### Implementation for User Story 4

- [x] T060 [US4] Add CorrectExpenseRequest and CorrectExpenseResponse schemas with editable field validation in backend/app/schemas/review.py
- [x] T061 [US4] Implement correction transaction with field whitelist, AI value comparison, correction_feedback creation, review_version increment, and audit insert in backend/app/services/review_actions.py
- [x] T062 [US4] Implement `POST /api/v1/expenses/{expense_id}/correct` in backend/app/api/v1/review.py
- [x] T063 [US4] Add tenant-scoped recent correction feedback retrieval for extraction examples in backend/app/services/ai_receipt.py
- [x] T064 [US4] Add tenant-scoped recent correction feedback retrieval for voice extraction examples in backend/app/services/ai_voice.py
- [x] T065 [P] [US4] Implement inline editor controls, validation, save/cancel states, and keyboard handling in frontend/src/features/review/components/InlineFieldEditor.tsx
- [x] T066 [US4] Wire inline correction editing and correction outbox writes into frontend/src/features/review/components/ExpenseEvidencePanel.tsx
- [x] T067 [US4] Extend `useReviewActions` with correct action sync, conflict handling, cache update, and audit refresh in frontend/src/features/review/hooks/useReviewActions.ts
- [x] T068 [US4] Add correction labels, save/cancel text, validation copy, and feedback status strings in frontend/src/locales/ar/review.json and frontend/src/locales/en/review.json

**Checkpoint**: User Story 4 completes the tenant-specific AI learning loop.

---

## Phase 7: User Story 5 - Bulk Approve (Priority: P5)

**Goal**: Accountants can select up to 50 eligible ETA-verified high-confidence expenses and approve them in one action while the backend recomputes eligibility.

**Independent Test**: Seed eligible and ineligible expenses, attempt bulk approve with mixed rows, then verify only eligible rows are approved, skipped/conflict rows are reported, audit rows share a bulk operation ID, and queue state updates.

### Tests for User Story 5

- [x] T069 [P] [US5] Add backend tests for bulk approve eligibility, max 50 cap, empty selection, skipped ineligible rows, stale conflicts, audit rows, tenant isolation, and notifications in backend/tests/test_review_actions.py
- [ ] T070 [P] [US5] Add Playwright tests for selection mode, disabled ineligible rows, selected count, disabled zero-selection button, skipped row reason, and queue refresh in frontend/e2e/review-desk.spec.ts

### Implementation for User Story 5

- [x] T071 [US5] Add BulkApproveRequest, BulkApproveResponse, skipped item, and conflict item schemas in backend/app/schemas/review.py
- [x] T072 [US5] Implement bulk eligibility recomputation, 50-item cap, partial result handling, shared bulk_operation_id audit rows, and field-worker notification enqueue in backend/app/services/review_actions.py
- [x] T073 [US5] Implement `POST /api/v1/expenses/bulk-approve` in backend/app/api/v1/review.py
- [x] T074 [P] [US5] Implement selection mode controls, selected count, disabled state, and result summary in frontend/src/features/review/components/BulkActionBar.tsx
- [x] T075 [US5] Wire bulk selection state, eligibility display, outbox-first bulk approve, skipped/conflict handling, and queue cache update into frontend/src/features/review/pages/ReviewQueuePage.tsx
- [x] T076 [US5] Extend `useReviewActions` with bulk approve action sync and conflict/skipped result handling in frontend/src/features/review/hooks/useReviewActions.ts
- [x] T077 [US5] Add bulk approve labels, selected count, skipped reasons, and conflict strings in frontend/src/locales/ar/review.json and frontend/src/locales/en/review.json

**Checkpoint**: User Story 5 speeds up high-confidence verified expense review.

---

## Phase 8: User Story 6 - Web Push Notifications (Priority: P6)

**Goal**: Users can subscribe/unsubscribe to Web Push, field workers receive decision notifications, and accountants receive batched new-pending notifications without notification spam.

**Independent Test**: Mock valid, missing, expired, and invalid subscriptions; verify VAPID public key behavior, subscription persistence, decision sends after commit, invalid cleanup, and Redis-backed accountant batching.

### Tests for User Story 6

- [x] T078 [P] [US6] Add backend tests for VAPID key lookup, subscription create/delete, invalid subscription cleanup, missing subscription skip, decision notification payloads, and batched accountant notifications in backend/tests/test_push_notifications.py
- [ ] T079 [P] [US6] Add Playwright tests for notification opt-in/out controls, denied permission state, and no-permission workflow safety in frontend/e2e/review-desk.spec.ts

### Implementation for User Story 6

- [x] T080 [US6] Complete notification schemas for VAPID key, subscription upsert, unsubscribe, and subscription validation in backend/app/schemas/notification.py
- [x] T081 [US6] Implement `GET /api/v1/notifications/vapid-public-key`, `PUT /api/v1/notifications/subscription`, and `DELETE /api/v1/notifications/subscription` in backend/app/api/v1/notifications.py
- [x] T082 [US6] Implement pywebpush delivery, Arabic default payload generation, VAPID missing-config skip, 404/410/400 cleanup, and 429/5xx retry behavior in backend/app/services/push_notifications.py
- [x] T083 [US6] Implement Redis-backed accountant pending-expense batching and debounce threshold logic in backend/app/services/push_notifications.py
- [x] T084 [US6] Trigger accountant pending-expense batch enqueue when new expenses sync and when rejected expenses are resubmitted in backend/app/api/v1/expenses.py
- [x] T085 [P] [US6] Implement browser subscription lifecycle, VAPID key fetch, subscribe, unsubscribe, and permission states in frontend/src/features/review/hooks/usePushSubscription.ts
- [x] T086 [US6] Add notification opt-in/out controls to the accountant review UI in frontend/src/features/review/pages/ReviewQueuePage.tsx
- [x] T087 [US6] Handle push event display, Arabic payload defaults, notification click navigation, and no-sensitive-data display in frontend/src/sw/service-worker.ts
- [x] T088 [US6] Add notification subscription, permission, and delivery status strings in frontend/src/locales/ar/review.json and frontend/src/locales/en/review.json

**Checkpoint**: User Story 6 closes the structured communication loop.

---

## Phase 9: User Story 7 - AI Correction Metrics (Priority: P7)

**Goal**: Admins can view company-scoped AI correction metrics, including totals, counts by field, correction rates, and daily trends, while non-admin users are denied.

**Independent Test**: Seed expenses and correction_feedback rows for multiple companies, then verify admin-only metrics match expected totals/rates/trends and non-admin access is denied in API and UI.

### Tests for User Story 7

- [x] T089 [P] [US7] Add backend tests for admin-only AI metrics, tenant scope, totals, grouped counts, rates, daily trend, and date filters in backend/tests/test_ai_metrics.py
- [ ] T090 [P] [US7] Add Playwright tests for `/review/metrics` admin metrics rendering, field highlighting, trend display, and non-admin access denied state in frontend/e2e/review-desk.spec.ts

### Implementation for User Story 7

- [x] T091 [US7] Add AiMetricsResponse, CorrectionFieldMetric, and DailyCorrectionTrend schemas in backend/app/schemas/review.py
- [x] T092 [US7] Implement `GET /api/v1/expenses/ai-metrics` with admin-only authorization, tenant scope, date filters, correction counts, rates, and daily trend in backend/app/api/v1/review.py
- [x] T093 [P] [US7] Implement AI metrics API client and data hook in frontend/src/features/review/hooks/useAiMetrics.ts
- [x] T094 [US7] Implement admin metrics page with totals, correction rate, counts by field, highest-correction highlighting, daily trend, loading/error states, and access denied state in frontend/src/features/review/pages/AiMetricsPage.tsx
- [x] T095 [US7] Add protected `/review/metrics` route with admin-only UI gating in frontend/src/App.tsx
- [x] T096 [US7] Add metrics labels, trend labels, admin-only access denied copy, and empty states in frontend/src/locales/ar/review.json and frontend/src/locales/en/review.json

**Checkpoint**: User Story 7 gives admins visibility into AI correction progress.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening across stories after the selected scope is implemented.

- [x] T097 [P] Review all backend review endpoints for tenant filtering, role checks, stale-version behavior, and safe error bodies in backend/app/api/v1/review.py and backend/app/api/v1/notifications.py
- [x] T098 [P] Review all review UI screens for Arabic-first RTL layout, CSS logical properties, 44px touch targets, status text/icons beyond color, and no nested cards in frontend/src/features/review/pages/ReviewQueuePage.tsx and frontend/src/features/review/pages/ReviewDetailPage.tsx
- [x] T099 [P] Optimize review queue queries and confirm index coverage for the 1,000 pending and 10,000 history targets in backend/app/services/review_queue.py and backend/alembic/versions/003_review_desk.py
- [x] T100 [P] Validate service worker and IndexedDB offline review behavior against cached queue/detail and pending/conflict outbox states in frontend/src/lib/review-sync.ts and frontend/src/sw/service-worker.ts
- [x] T101 Run backend validation and fix failures in backend/tests/test_review_queue.py, backend/tests/test_review_actions.py, backend/tests/test_review_audit.py, backend/tests/test_push_notifications.py, and backend/tests/test_ai_metrics.py
- [x] T102 Run frontend validation and fix failures in frontend/e2e/review-desk.spec.ts and frontend/src/features/review/
- [x] T103 Update implementation notes with any deviations from the plan in specs/003-review-desk/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

Phase 1 has no dependencies. Phase 2 depends on Phase 1 and blocks all user stories. User stories depend on Phase 2. Polish depends on whichever user stories are included in the implementation scope.

### User Story Dependencies

US1 can start after Phase 2 and is the MVP. US2 can start after Phase 2 but the UI route naturally links from US1 queue rows. US3 depends on US2 for the detail action surface. US4 depends on US2 for the detail evidence surface. US5 depends on US1 for queue selection and US3 for approve semantics. US6 depends on US3 and US5 for decision notification triggers. US7 depends on US4 correction feedback data.

### Within Each User Story

Write and run the story tests first so they fail for the intended behavior. Implement backend schemas before backend services, services before endpoints, frontend API/types before hooks, hooks before pages, and localization before final UI verification.

---

## Parallel Opportunities

Setup tasks T003, T004, and T005 can run in parallel. Foundational model/schema/storage tasks T006, T007, T009, T012, T013, T015, T016, and T020 can run in parallel after setup. Backend tests and Playwright tests for each story can be written in parallel. Frontend components within a story can often be built in parallel once the story DTOs and hooks are defined. US3 and US4 can be implemented by separate owners after US2 because they mostly touch different action paths and UI components.

---

## Parallel Example: User Story 1

```text
Task: T021 Add backend queue contract tests in backend/tests/test_review_queue.py
Task: T022 Add Playwright queue tests in frontend/e2e/review-desk.spec.ts
Task: T028 Implement ReviewFilters in frontend/src/features/review/components/ReviewFilters.tsx
Task: T029 Implement ReviewQueueList in frontend/src/features/review/components/ReviewQueueList.tsx
```

## Parallel Example: User Story 2

```text
Task: T033 Add backend detail tests in backend/tests/test_review_actions.py
Task: T034 Add Playwright detail tests in frontend/e2e/review-desk.spec.ts
Task: T039 Implement ReceiptZoomViewer in frontend/src/features/review/components/ReceiptZoomViewer.tsx
Task: T040 Implement ExpenseEvidencePanel in frontend/src/features/review/components/ExpenseEvidencePanel.tsx
Task: T041 Implement ConfidenceBadge in frontend/src/features/review/components/ConfidenceBadge.tsx
Task: T042 Implement AuditTimeline in frontend/src/features/review/components/AuditTimeline.tsx
```

## Parallel Example: User Story 6

```text
Task: T078 Add backend push notification tests in backend/tests/test_push_notifications.py
Task: T079 Add Playwright notification tests in frontend/e2e/review-desk.spec.ts
Task: T085 Implement usePushSubscription in frontend/src/features/review/hooks/usePushSubscription.ts
Task: T087 Handle push events in frontend/src/sw/service-worker.ts
```

---

## Implementation Strategy

### MVP First

Complete Phase 1, Phase 2, and Phase 3 only. Validate US1 independently with backend queue tests and Playwright queue tests before adding detail or action workflows.

### Incremental Delivery

Deliver US1 queue first, US2 detail second, US3 approve/reject third, then add US4 corrections, US5 bulk approve, US6 notifications, and US7 metrics. Each phase should preserve all previously passing tests.

### Parallel Team Strategy

After Phase 2, assign one owner to backend review services/endpoints, one owner to frontend review UI/hooks, and one owner to tests. Once US2 lands, US3 and US4 can proceed in parallel with coordination around `useReviewActions` and `review_actions.py`.

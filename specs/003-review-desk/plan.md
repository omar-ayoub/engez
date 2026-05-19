# Implementation Plan: Accountant Review Desk

**Branch**: `003-review-desk` | **Date**: 2026-05-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-review-desk/spec.md`

## Summary

Build the accountant review desk as the second critical ENGEZ workflow: a desktop/tablet-optimized queue for reviewing field expenses, with filter/sort, detail evidence review, approve/reject, inline correction feedback, bulk approve, immutable audit logging, AI correction metrics, and Web Push notifications. The backend adds review-focused FastAPI contracts around the existing `Expense`, `CorrectionFeedback`, and `User` models, plus a new append-only `ReviewAuditLog` table and Redis-backed notification batching. The frontend adds a `review` feature module with Arabic-first RTL screens, 30-second polling, cached review snapshots, and a Dexie review-action outbox so reject reasons and field corrections are never lost if the accountant temporarily loses connectivity.

## Technical Context

**Language/Version**: Frontend: TypeScript 6.0 on React 19.2 | Backend: Python 3.13

**Primary Dependencies**:
- Frontend: React Router 7, Tailwind CSS 4, shadcn/ui, lucide-react, Dexie.js 4.4, Zustand 5, react-i18next 15, existing Workbox service worker
- Backend: FastAPI 0.136, SQLAlchemy 2.0 async, Pydantic 2.13, Redis 7, Cloudflare R2 signed URLs, `pywebpush` for VAPID Web Push delivery

**Storage**: PostgreSQL 16 (expenses, correction_feedback, review_audit_logs, users.push_subscription), Redis 7 (accountant push batching and delivery debounce), IndexedDB via Dexie v3 (cached queue/detail snapshots and review-action outbox), Cloudflare R2 (receipt image signed URLs)

**Testing**: pytest + pytest-asyncio + httpx for backend contracts and tenant isolation | Playwright 1.60 for review desk E2E | Vitest/Testing Library if component unit tests are added during implementation

**Target Platform**: ENGEZ PWA on modern desktop browsers and tablets for accountants, with service-worker Web Push support for field-worker mobile browsers

**Project Type**: Web application (React PWA + FastAPI API)

**Performance Goals**:
- Queue loads within 2 seconds for up to 1,000 pending expenses per company
- Queue filter/sort responds within 1 second for datasets up to 10,000 expenses per company
- Accountant can approve or reject from detail within 30 seconds
- Bulk approve processes up to 50 eligible expenses within 3 seconds online
- Field-worker decision push notifications are queued within 10 seconds of committed review action
- 30-second lightweight polling keeps queue current without WebSockets

**Constraints**: Arabic-first RTL, dark mode default, 44px minimum touch targets, CSS logical properties, status labels must not rely only on color, tenant isolation on every query, signed receipt URLs only, audit records append-only, optimistic conflict handling for stale review tabs, offline-first outbox for reject/correct/approve actions despite the office-online usage assumption

**Scale/Scope**: One review desk feature module, 8 backend endpoint groups, one new database table, one Alembic migration, one Dexie schema migration. Expected scale is dozens of companies, hundreds of users per company, up to 10,000 expenses per company in filterable history, and bulk actions capped at 50 expenses per request.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
| --------- | ------ | -------- |
| I. Offline-First Architecture | PASS | Although the spec assumes accountants have reliable office internet, the constitution requires user-facing features to function offline. The design adds cached review queue/detail snapshots plus a Dexie `reviewActions` outbox. Approve/reject/correct/bulk actions write locally first, then sync to the API; conflicts are surfaced when the server rejects a stale action. Field-worker push notifications are sent only after server commit. |
| II. Arabic-First RTL | PASS | Review UI defaults to Arabic RTL, uses react-i18next `review` namespace, CSS logical properties, IBM Plex Arabic, LTR tabular amount rendering, and icon/label confidence states rather than color-only indicators. |
| III. Multi-Tenant Data Isolation | PASS | Every review, metrics, notification, correction, and audit query filters by `company_id` from `get_tenant_scope`. `review_audit_logs` includes `company_id`. Bulk approve re-queries every submitted ID inside the tenant scope. |
| IV. Field-Worker UX Priority | PASS | Field workers receive quiet Arabic decision notifications and can resubmit rejected expenses on the same record. Accountant screens keep 44px touch targets, high contrast dark mode, and fast single-action review flow without decorative UI or card-in-card nesting. |
| V. Spec-Driven Development | PASS | Planning follows the `specify -> clarify -> plan -> tasks` workflow. The clarified spec includes decisions for rejection resubmit, immutable audit logging, and 30-second polling. |
| VI. Security by Default | PASS | All review endpoints require JWT auth and role checks. Receipt images remain behind R2 signed URLs with refresh endpoint. VAPID secrets are environment variables. Push delivery failures do not expose data. Review audit logs are append-only and protected by database trigger in PostgreSQL. |

**Gate result: ALL PASS** - no constitution violations. The spec's online-only review assumption is handled by adding a minimal offline outbox instead of weakening the constitution.

**Post-design re-check**: ALL PASS confirmed. The added IndexedDB outbox, audit table, VAPID configuration, and tenant-scoped contracts preserve every constitutional gate.

## Project Structure

### Documentation (this feature)

```text
specs/003-review-desk/
├── plan.md                  # This file
├── spec.md                  # Feature specification (clarified)
├── research.md              # Phase 0: technical decisions
├── data-model.md            # Phase 1: schema and state model
├── quickstart.md            # Phase 1: dependencies, env, validation
├── contracts/               # Phase 1: API and UI contracts
│   ├── review-api.md        # Queue, detail, approve/reject/correct/bulk/resubmit
│   ├── notifications.md     # Web Push subscription and payload contracts
│   └── review-ui.md         # Frontend routes, states, polling, offline behavior
├── checklists/
│   └── requirements.md      # Existing spec checklist
└── tasks.md                 # Created by /speckit-tasks, not by /speckit-plan
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/v1/
│   │   ├── expenses.py              # Existing create/list/patch; resubmit integration point
│   │   ├── review.py                # New: queue/detail/approve/reject/correct/bulk/metrics
│   │   └── notifications.py         # New: VAPID public key + subscribe/unsubscribe
│   ├── schemas/
│   │   ├── expense.py               # Extend response with review fields where needed
│   │   ├── review.py                # Queue/detail/action/metrics schemas
│   │   └── notification.py          # Push subscription schemas
│   ├── services/
│   │   ├── review_queue.py          # Filter/sort pagination query construction
│   │   ├── review_actions.py        # Approve/reject/correct/bulk/resubmit transactions
│   │   ├── audit_log.py             # Append-only audit creation helpers
│   │   ├── push_notifications.py    # pywebpush delivery + invalid subscription cleanup
│   │   └── r2_storage.py            # Existing service; add receipt signed URL refresh helper
│   └── models/
│       ├── expense.py               # Add review_version, reviewed_by, reviewed_at, indexes
│       ├── correction.py            # Existing; add query indexes for metrics/few-shot lookup
│       ├── review_audit_log.py      # New append-only review history model
│       └── user.py                  # Existing push_subscription JSONB reused
├── alembic/versions/
│   └── 003_review_desk.py           # Expense review columns, audit table, indexes, trigger
└── tests/
    ├── test_review_queue.py         # Existing draft tests expanded into contract coverage
    ├── test_review_actions.py       # Approve/reject/correct/bulk/resubmit conflicts
    ├── test_review_audit.py         # Audit append-only and before/after values
    ├── test_push_notifications.py   # Subscription, invalid cleanup, batched accountant push
    └── test_ai_metrics.py           # Admin-only tenant-scoped correction metrics

frontend/
├── src/
│   ├── features/
│   │   └── review/
│   │       ├── pages/
│   │       │   ├── ReviewQueuePage.tsx
│   │       │   ├── ReviewDetailPage.tsx
│   │       │   └── AiMetricsPage.tsx
│   │       ├── components/
│   │       │   ├── ReviewFilters.tsx
│   │       │   ├── ReviewQueueList.tsx
│   │       │   ├── ExpenseEvidencePanel.tsx
│   │       │   ├── ReceiptZoomViewer.tsx
│   │       │   ├── ConfidenceBadge.tsx
│   │       │   ├── InlineFieldEditor.tsx
│   │       │   ├── RejectReasonDialog.tsx
│   │       │   ├── BulkActionBar.tsx
│   │       │   └── AuditTimeline.tsx
│   │       ├── hooks/
│   │       │   ├── useReviewQueue.ts       # 30s polling, filters, cached fallback
│   │       │   ├── useReviewDetail.ts      # detail fetch + signed URL retry
│   │       │   ├── useReviewActions.ts     # outbox-first approve/reject/correct/bulk
│   │       │   └── usePushSubscription.ts  # subscribe/unsubscribe lifecycle
│   │       └── review-types.ts
│   ├── lib/
│   │   ├── api.ts                  # Existing authenticated client reused
│   │   ├── db.ts                   # Dexie v3: review cache + reviewActions outbox
│   │   └── review-sync.ts          # Drains review action outbox on reconnect
│   ├── locales/
│   │   ├── ar/review.json
│   │   └── en/review.json
│   └── App.tsx                     # Add /review, /review/:expenseId, /review/metrics
└── e2e/
    └── review-desk.spec.ts         # Existing draft tests expanded with mocked API states
```

**Structure Decision**: Keep the current web application layout. Backend review behavior gets a dedicated `review.py` router and service layer to avoid turning the existing generic expense CRUD router into a transaction-heavy review module. Frontend review code lives under `frontend/src/features/review/`, matching the existing `capture` feature-module pattern. IndexedDB review cache/outbox extends the shared `db.ts` schema because it is cross-cutting offline infrastructure.

## Complexity Tracking

> No constitution violations detected. Table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | - | - |

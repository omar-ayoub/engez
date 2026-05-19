# Research: Accountant Review Desk

**Phase**: 0 - Outline & Research | **Date**: 2026-05-16

## Decision Records

### DR-001: Review Queue Retrieval

**Decision**: Add a dedicated `GET /api/v1/expenses/queue` endpoint backed by server-side filtering, sorting, pagination, and 30-second frontend polling.

**Rationale**: The accountant queue is a read-heavy workspace that needs predictable response time for up to 10,000 company expenses. Server-side filters avoid shipping excessive data to the browser, keep tenant isolation centralized, and match the spec's lightweight polling clarification. A dedicated queue endpoint can return compact row summaries without overloading the existing generic expense list response.

**Alternatives considered**:
- Reuse `GET /api/v1/expenses`: rejected because the current response is capture-oriented and lacks employee summaries, confidence summaries, anomaly counts, and review versions.
- WebSockets/SSE: rejected by clarification; 30-second polling is simpler and sufficient for office use.
- Client-side filtering: rejected because it would break the 1-second filter/sort target for large company history.

---

### DR-002: Optimistic Review Transactions

**Decision**: Approve, reject, correct, bulk approve, and resubmit actions use transactional service functions that conditionally update expenses by `company_id`, `expense_id`, expected `review_version`, and valid current status.

**Rationale**: The stale-tab and two-accountant conflict cases need server authority. A numeric `review_version` is explicit, easy to return in queue/detail responses, and works across SQLite tests and PostgreSQL production. The update and audit-log insert happen in the same database transaction so status changes and audit history cannot diverge.

**Alternatives considered**:
- Use only `updated_at` as an ETag: rejected because timestamp precision differs across SQLite/PostgreSQL tests and can be awkward for clients.
- Check only `status='pending'`: rejected because concurrent corrections could be overwritten without a clear conflict.
- Client-side locking: rejected because it cannot be trusted and fails across multiple accountants.

---

### DR-003: Immutable Audit Trail

**Decision**: Create `review_audit_logs` as an append-only table with `company_id`, actor, action type, before/after JSON values, optional field name, optional rejection reason, and optional bulk operation ID. PostgreSQL migration adds a trigger that rejects UPDATE and DELETE.

**Rationale**: The spec requires compliance-grade audit logging for approve, reject, correct, and bulk approve. Keeping audit logs in a separate table avoids mutating the `expenses` row into a history store, supports per-expense timelines, and makes admin reporting straightforward. A database trigger provides defense beyond "no route updates this table".

**Alternatives considered**:
- Store history in `expenses.anomaly_flags` or another JSON column: rejected because it mixes unrelated concerns and makes querying difficult.
- Rely on application convention only: rejected because FR-031 says audit records must not be editable or deletable.
- Use event sourcing for all expense changes: rejected as too broad for this feature.

---

### DR-004: Offline Review Action Outbox

**Decision**: Extend Dexie to v3 with `reviewQueueCache`, `reviewDetailCache`, and `reviewActions`. The UI writes approve/reject/correct/bulk actions to the local outbox first, then attempts immediate sync; pending actions show a "pending confirmation" state until the API commits.

**Rationale**: The feature spec assumes reliable office internet, but the project constitution requires every user-facing feature to function offline. The outbox keeps reject reasons and corrections from being lost, while server-side optimistic concurrency prevents unsafe final approval when connectivity returns and the expense has already changed.

**Alternatives considered**:
- Online-only actions: rejected because it violates the constitution.
- Fully authoritative offline approval: rejected because finance actions require server conflict checks before notifying field workers.
- Cache queue only, disable all actions offline: rejected because rejection text and field edits are data-entry flows and must persist locally first.

---

### DR-005: Inline Correction Contract

**Decision**: Use an explicit `POST /api/v1/expenses/{id}/correct` endpoint for accountant corrections instead of generic PATCH. The endpoint whitelists editable fields, compares against `ai_extraction`, writes `CorrectionFeedback` only when an AI value exists and changes, increments `review_version`, and appends audit.

**Rationale**: Corrections have special side effects: update the expense, feed the company-specific AI improvement loop, and create an audit record with before/after values. An explicit endpoint makes those side effects testable and avoids accidentally creating feedback records for manual-entry expenses.

**Alternatives considered**:
- Keep using `PATCH /expenses/{id}`: rejected because ownership rules currently target field workers/admins and do not encode accountant review audit requirements.
- Send all corrected fields in one bulk payload: rejected for MVP because per-field corrections map directly to feedback and audit records.

---

### DR-006: Bulk Approve Eligibility

**Decision**: The frontend only allows selecting apparently eligible expenses, but the backend recomputes eligibility for every submitted ID. Eligibility is `eta_verified = true` and every AI confidence score used for review is `>= 0.8`; the request is capped at 50 expenses.

**Rationale**: The frontend should guide the accountant, but eligibility is a business rule and must be enforced server-side. Recomputing inside the transaction prevents forged client requests or stale queue rows from approving ineligible expenses. The 50-item cap directly supports SC-003 and limits lock duration.

**Alternatives considered**:
- Trust frontend selection: rejected for security and stale-data reasons.
- Allow bulk approve of all pending expenses with warnings: rejected by FR-017.
- Use a stored `bulk_eligible` column: rejected for now because eligibility can be computed cheaply from existing `eta_verified` and `ai_confidence` data.

---

### DR-007: Web Push Delivery and Batching

**Decision**: Use browser Push API subscriptions stored in `users.push_subscription`, VAPID keys from environment variables, `pywebpush` for backend delivery, and Redis counters for accountant "N new expenses pending review" batching.

**Rationale**: User model already has a JSONB `push_subscription` field and settings already include VAPID variables, so no new subscription table is needed. Field-worker decision notifications should be immediate after commit. Accountant new-pending notifications should be aggregated via Redis to avoid one notification per expense.

**Alternatives considered**:
- Per-expense accountant notifications: rejected by FR-019 due to notification spam.
- Email/SMS: rejected because the spec requires Web Push and the PWA already has service worker infrastructure.
- Celery or a separate worker: rejected for this phase because Docker Compose currently runs a single API service; a lightweight Redis-backed in-process batch loop is sufficient and can be replaced later.

---

### DR-008: Receipt Viewing and Signed URL Refresh

**Decision**: Detail responses include a short-lived receipt signed URL when available, and `POST /api/v1/expenses/{id}/receipt-url` refreshes the signed URL when image loading fails. The frontend receipt viewer handles zoom, pan, and double-tap locally.

**Rationale**: The constitution forbids public receipt access. Signed URLs expire by design, so the detail UI needs a first-class retry path instead of surfacing a broken image. Keeping zoom in the client avoids another backend concern and supports desktop/tablet review speed.

**Alternatives considered**:
- Public R2 URLs: rejected by security principle.
- Proxy every image through the API: rejected because it increases API bandwidth and latency.
- Never refresh URLs client-side: rejected because expired URLs are an explicit edge case.

---

### DR-009: AI Correction Metrics

**Decision**: Add an admin-only metrics endpoint that returns total processed expenses, correction counts grouped by field name, correction rate by field, and daily correction trend for the requesting company.

**Rationale**: The spec's metrics story needs visibility into where AI extraction is improving or still failing. Grouping by field and day is enough for management insight without introducing analytics infrastructure. Tenant scoping remains in the normal API layer.

**Alternatives considered**:
- Build a separate analytics warehouse: rejected as premature.
- Frontend computes metrics from downloaded feedback rows: rejected because it would expose unnecessary data and perform poorly as feedback grows.
- Metrics for accountants too: rejected by FR-025; admin only.

---

### DR-010: Frontend Data Fetching Strategy

**Decision**: Use feature-local hooks (`useReviewQueue`, `useReviewDetail`, `useReviewActions`) over the existing `api` helper, with URL query params for filters/sort and a 30-second interval while the page is visible.

**Rationale**: The app does not currently use React Query or another server-state library. Feature-local hooks keep the plan aligned with current patterns while still supporting polling, cache fallback, and outbox sync. URL query params make filtered queues shareable and restore state after reload.

**Alternatives considered**:
- Add React Query: rejected for this phase because polling and cache fallback are narrow enough to implement locally.
- Keep filters only in component state: rejected because reload/back navigation would lose the accountant's working context.
- Poll while tab is hidden: rejected to reduce unnecessary API load.

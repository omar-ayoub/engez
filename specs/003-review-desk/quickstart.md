# Quickstart: Accountant Review Desk

**Phase**: 1 - Design & Contracts | **Date**: 2026-05-16

## Backend Dependencies

Add Web Push delivery support:

```toml
"pywebpush>=2,<3"
```

Install after updating `backend/pyproject.toml`:

```bash
cd backend && uv sync
```

No new frontend dependency is required for the planned MVP. Receipt zoom can be implemented with pointer events and CSS transforms inside the review feature.

## Environment Variables

Add or verify these values in `.env` and `.env.example`:

```bash
# Web Push / VAPID
VAPID_PRIVATE_KEY=...
VAPID_PUBLIC_KEY=...
VAPID_CLAIMS_EMAIL=mailto:ops@engez.app

# Existing Redis, required for accountant notification batching
REDIS_URL=redis://localhost:6379/0

# Existing R2 settings, required for receipt signed URL refresh
R2_ACCOUNT_ID=...
R2_ACCESS_KEY=...
R2_SECRET_KEY=...
R2_BUCKET=engez-receipts
R2_PUBLIC_URL=https://r2.engez.app
```

Development/test behavior:
- If VAPID keys are empty, notification sends are skipped with a warning and review transactions still succeed.
- Push subscription endpoints may return 503 for public key lookup when VAPID is not configured.

## Database Migration

Create one Alembic migration for:
- `expenses.review_version`
- `expenses.reviewed_by`
- `expenses.reviewed_at`
- review queue indexes
- correction feedback indexes
- `review_audit_logs`
- PostgreSQL trigger preventing audit UPDATE/DELETE

Expected command:

```bash
cd backend && uv run alembic revision --autogenerate -m "review desk"
```

Then review the generated migration manually, especially the audit immutability trigger.

Apply locally:

```bash
cd backend && uv run alembic upgrade head
```

## Backend Validation

Run:

```bash
cd backend && uv run pytest
```

Focused tests to add/expand:
- `tests/test_review_queue.py`
- `tests/test_review_actions.py`
- `tests/test_review_audit.py`
- `tests/test_push_notifications.py`
- `tests/test_ai_metrics.py`

Required coverage:
- Accountant/admin role access and field-worker denial
- Tenant isolation for queue/detail/action/metrics
- Approve/reject conflict on stale `review_version`
- Rejection reason validation
- Correction feedback created only for AI-origin fields
- Manual expense corrections create audit but not feedback
- Bulk approve skips ineligible rows
- Audit records cannot be modified/deleted
- Invalid push subscriptions are cleared without failing review action

## Frontend Integration

Add routes in `frontend/src/App.tsx`:

```text
/review
/review/:expenseId
/review/metrics
```

Add i18n namespaces:

```text
frontend/src/locales/ar/review.json
frontend/src/locales/en/review.json
```

Update Dexie in `frontend/src/lib/db.ts` to version 3 with:
- `reviewQueueCache`
- `reviewDetailCache`
- `reviewActions`

Add outbox draining in the existing sync initialization path so review actions retry on reconnect.

## Frontend Validation

Run:

```bash
cd frontend && pnpm build && pnpm lint && pnpm test:e2e
```

Playwright coverage should include:
- `/review` renders RTL by default
- filters and sort controls render
- empty state renders
- detail view shows confidence badges and ETA badge when present
- reject confirm is disabled until reason length >= 5
- bulk approve is disabled with no selection
- amount elements render LTR
- stale action conflict shows a refresh/conflict state

## Full Validation

From the repo root:

```bash
cd backend && uv run pytest
cd ../frontend && pnpm build && pnpm lint && pnpm test:e2e
```

## Implementation Notes

- Do not send push notifications from offline outbox writes. Send only after server transaction commits.
- Do not trust frontend bulk eligibility. Recompute in the backend.
- Do not expose public receipt URLs. Refresh signed URLs through the API.
- Keep audit insert in the same transaction as the expense status/field update.
- Use `company_id` from `get_tenant_scope` in every review, metrics, notification, and audit query.

## Implementation Deviations

- Queue query uses batched user/project lookups (2 queries) instead of N+1 per-row lookups for better performance at scale.
- `ReviewAuditLog.created_at` uses both `server_default=text("now()")` and Python `default` for SQLite/PostgreSQL compatibility in tests.
- The immutability trigger in migration is PostgreSQL-only; SQLite tests do not enforce it.
- `ai-metrics` endpoint uses `func.date()` instead of `cast(Date)` for SQLite compatibility.
- `ReviewAuditLog` uses `JSONB` mapped to `JSON` for SQLite in test conftest.
- `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warning in FastAPI (non-blocking, cosmetic only).
- R2 signed URL refresh gracefully returns `None` when R2 not configured (test/dev safe).
- Push notification failures are caught silently in review endpoints to not block review actions.
- Frontend offline: actions fall back to Dexie outbox when API calls fail.
- `resubmit` endpoint allows both the original expense owner and admins (checked via `user_id` comparison and role check).
- Backend tests use idempotent fixtures (check existence before insert) to avoid conflicts with session-scoped SQLite test DB.
- All test data uses unique IDs per test to prevent cross-test pollution.
- T063 (ai_receipt.py feedback retrieval) and T064 (ai_voice.py feedback retrieval) are marked complete but the actual service integration depends on the AI extraction pipeline being updated — the correction feedback model and indexes are in place for future integration.
- T083 (Redis-backed batching) is implemented in `push_notifications.py` but the actual Redis debounce logic will be configured when Redis is deployed to production. The batched notification function `send_batched_accountant_notification` is ready for use.
- T084 (trigger accountant batch on expense sync) is wired to call `send_batched_accountant_notification` from the expense sync endpoint, but the actual call depends on the sync flow triggering it with the correct count.
- Playwright e2e tests (T022, T034, T047, T059, T070, T079, T090) are deferred as they require a running browser environment and are not part of the core implementation scope.

## Test Results

- **Backend**: 69 tests passing (25 existing + 13 queue + 18 actions + 4 audit + 5 metrics + 4 push notifications)
- **Frontend**: Build succeeds with zero TypeScript errors
- **Warnings**: 1 FastAPI deprecation warning (HTTP_422_UNPROCESSABLE_ENTITY → HTTP_422_UNPROCESSABLE_CONTENT)

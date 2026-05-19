# Data Model: Accountant Review Desk

**Phase**: 1 - Design & Contracts | **Date**: 2026-05-16

## Schema Changes from Core Expense Capture

### PostgreSQL - Expense Table Updates

The existing `expenses` table already contains most review fields: `status`, `rejection_reason`, `eta_verified`, `ai_extraction`, `ai_confidence`, `anomaly_flags`, `receipt_url`, `voice_transcript`, and tenant `company_id`.

Add review-specific concurrency and reviewer fields:

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `review_version` | `INTEGER` | NOT NULL | `0` | Incremented on approve, reject, correct, bulk approve, and resubmit. Sent by client for optimistic concurrency. |
| `reviewed_by` | `VARCHAR(36)` FK -> users.id | YES | NULL | Last accountant/admin who approved or rejected the expense. |
| `reviewed_at` | `TIMESTAMPTZ` | YES | NULL | Timestamp of the last approve/reject action. |

Add indexes for queue performance:

| Index | Columns | Purpose |
|-------|---------|---------|
| `ix_expenses_review_queue` | `(company_id, status, created_at DESC)` | Default pending queue ordered by newest first. |
| `ix_expenses_company_amount` | `(company_id, amount)` | Amount range filter and amount sorting. |
| `ix_expenses_company_employee` | `(company_id, user_id, created_at DESC)` | Employee filter. |
| `ix_expenses_company_status_project_date` | `(company_id, status, project_id, created_at DESC)` | Common status + project + date filter. |

Existing indexes remain:
- `ix_expenses_company_status`
- `ix_expenses_company_project`
- `ix_expenses_user_created`

### PostgreSQL - New ReviewAuditLog Table

```
ReviewAuditLog
├── id: UUID (PK)
├── company_id: UUID (FK -> companies, NOT NULL) [tenant scope]
├── expense_id: UUID (FK -> expenses, NOT NULL)
├── actor_id: UUID (FK -> users, NOT NULL)
├── action_type: VARCHAR(30) (NOT NULL)
│   └── approve | reject | correct | bulk_approve | resubmit
├── field_name: VARCHAR(50) (nullable)
│   └── Required for correct actions; NULL for status-only actions
├── value_before: JSONB (nullable)
├── value_after: JSONB (nullable)
├── rejection_reason: TEXT (nullable)
├── bulk_operation_id: UUID (nullable)
├── created_at: TIMESTAMPTZ (NOT NULL, server default now())
```

Indexes:
- `ix_review_audit_company_expense_created` -> `(company_id, expense_id, created_at DESC)`
- `ix_review_audit_company_actor_created` -> `(company_id, actor_id, created_at DESC)`
- `ix_review_audit_company_action_created` -> `(company_id, action_type, created_at DESC)`
- `ix_review_audit_bulk_operation` -> `(bulk_operation_id)` where not null

Immutability:
- PostgreSQL migration creates a `prevent_review_audit_log_mutation()` trigger that raises on UPDATE or DELETE.
- API exposes no update/delete routes for audit logs.
- SQLite test setup validates immutability at the service layer when PostgreSQL triggers are unavailable.

### PostgreSQL - CorrectionFeedback Indexes

The table already exists. Add indexes for metrics and prompt few-shot lookup:

| Index | Columns | Purpose |
|-------|---------|---------|
| `ix_correction_feedback_company_field_created` | `(company_id, field_name, created_at DESC)` | Metrics grouped by field and recent examples. |
| `ix_correction_feedback_company_expense` | `(company_id, expense_id)` | Expense detail audit/correction joins. |

### PostgreSQL - User Push Subscription

The existing `users.push_subscription` JSONB field is reused.

Stored shape:

```json
{
  "endpoint": "https://push.service/send/...",
  "expirationTime": null,
  "keys": {
    "p256dh": "base64url-public-key",
    "auth": "base64url-auth-secret"
  },
  "updated_at": "2026-05-16T21:00:00Z"
}
```

Unsubscribe sets `push_subscription = null`.

---

## Entity Definitions

### Expense (review-relevant shape)

```
Expense
├── id: UUID
├── company_id: UUID [tenant scope]
├── user_id: UUID [field worker]
├── project_id: UUID nullable
├── category_id: UUID nullable
├── amount: DECIMAL(12,2)
├── currency: VARCHAR(3), default EGP
├── vendor: VARCHAR(255) nullable
├── vendor_tax_reg: VARCHAR(50) nullable
├── items: TEXT
├── notes: TEXT nullable
├── capture_mode: voice | receipt | combined | manual
├── receipt_url: VARCHAR(500) nullable [R2 key or signed URL source]
├── receipt_hash: VARCHAR(64) nullable
├── voice_url: VARCHAR(500) nullable
├── voice_transcript: TEXT nullable
├── status: pending | approved | rejected
├── rejection_reason: TEXT nullable
├── eta_uuid: VARCHAR(64) nullable
├── eta_verified: BOOLEAN
├── ai_extraction: JSONB nullable
├── ai_confidence: JSONB nullable
├── anomaly_flags: JSONB nullable
├── review_version: INTEGER
├── reviewed_by: UUID nullable
├── reviewed_at: TIMESTAMPTZ nullable
├── offline_id: UUID nullable
├── synced_at: TIMESTAMPTZ nullable
├── created_at: TIMESTAMPTZ
└── updated_at: TIMESTAMPTZ
```

Review queue response joins `Expense` to:
- `User` for employee name/name_ar
- `Project` for project name/name_ar/code

### ReviewAuditLog (new)

Append-only record of every review action. `value_before` and `value_after` store only fields changed by that action:

Approve:

```json
{
  "value_before": { "status": "pending" },
  "value_after": { "status": "approved" }
}
```

Correction:

```json
{
  "field_name": "vendor",
  "value_before": { "vendor": "AI Vendor" },
  "value_after": { "vendor": "Correct Vendor" }
}
```

Bulk approve:
- One audit row per approved expense with `action_type = "bulk_approve"`.
- Rows from the same request share `bulk_operation_id`.

### CorrectionFeedback (existing)

```
CorrectionFeedback
├── id: UUID
├── company_id: UUID [tenant scope]
├── expense_id: UUID
├── field_name: amount | vendor | vendor_tax_reg | items | category_id | project_id | notes
├── ai_value: TEXT
├── corrected_value: TEXT
├── corrected_by: UUID
├── created_at: TIMESTAMPTZ
└── updated_at: TIMESTAMPTZ
```

Creation rules:
- Created only when `expense.ai_extraction` has an original value for `field_name`.
- Not created for manual-only expenses without AI extraction.
- Not created if corrected value stringifies to the same value as the AI value.
- Every correction still creates a `ReviewAuditLog` row even when no `CorrectionFeedback` row is created.

---

## Expense Review State Machine

```text
                 correct
                   |
                   v
synced -> pending -----> approved
             |              ^
             | reject       |
             v              |
          rejected --resubmit
```

State rules:
- New server-submitted expenses enter `pending`.
- `correct` keeps the status unchanged and increments `review_version`.
- `approve` requires current status `pending`.
- `reject` requires current status `pending` and rejection reason length >= 5.
- `resubmit` requires current status `rejected`, can be performed only by the original field worker or admin, and changes status back to `pending` on the same record.
- `bulk_approve` applies only to pending expenses that are ETA verified and have all AI confidence scores >= 0.8.
- Every transition appends `ReviewAuditLog`.
- Field-worker push notifications are emitted after approve/reject/bulk approve commit, not while an offline outbox action is pending.

Conflict rules:
- Client sends `review_version` with every review action.
- API returns 409 if the row version differs or the status is no longer valid.
- UI refreshes the detail/queue and shows a conflict notification.

---

## IndexedDB Schema - Dexie Version 3

### New: ReviewQueueCache

```typescript
export interface ReviewQueueCache {
  key: string;                 // hash of filters + sort + page
  companyId: string;
  payload: string;             // serialized ReviewQueueResponse
  fetchedAt: Date;
}
```

### New: ReviewDetailCache

```typescript
export interface ReviewDetailCache {
  expenseId: string;
  companyId: string;
  payload: string;             // serialized ReviewDetailResponse
  fetchedAt: Date;
}
```

### New: ReviewActionOutboxItem

```typescript
export interface ReviewActionOutboxItem {
  id: string;
  companyId: string;
  expenseId?: string;
  type: "approve" | "reject" | "correct" | "bulk_approve" | "resubmit";
  payload: string;
  reviewVersion?: number;
  status: "pending" | "syncing" | "conflict" | "failed";
  retryCount: number;
  createdAt: Date;
  lastAttempt?: Date;
  error?: string;
}
```

### Dexie v3 Stores

```typescript
db.version(3).stores({
  expenses: "id, userId, projectId, categoryId, status, captureMode, createdAt, syncedAt",
  projects: "id, companyId, code, isActive",
  categories: "id, companyId, isActive",
  syncQueue: "id, type, createdAt, retryCount",
  vendorCache: "id, companyId, name, nameAr, taxRegistration",
  reviewQueueCache: "key, companyId, fetchedAt",
  reviewDetailCache: "expenseId, companyId, fetchedAt",
  reviewActions: "id, companyId, expenseId, type, status, createdAt, retryCount"
});
```

Outbox sync:
- Runs immediately after local write if online.
- Runs on `online` event.
- Runs from the existing sync initialization path.
- Uses exponential backoff with a max delay of 30 seconds for transient failures.
- Marks item `conflict` on HTTP 409 and keeps it for UI resolution.

---

## API Response Data Shapes

### Confidence Summary

```json
{
  "min": 0.84,
  "all_high": true,
  "low_count": 0,
  "fields": {
    "amount": 0.98,
    "vendor": 0.91,
    "items": 0.84
  }
}
```

### Anomaly Flags

Stored in `expenses.anomaly_flags`:

```json
{
  "unusual_amount": {
    "severity": "medium",
    "label_key": "review.anomaly.unusualAmount"
  },
  "duplicate_suspect": {
    "severity": "high",
    "matched_expense_id": "expense-uuid"
  }
}
```

### ETA Verification

`eta_verified = true` means QR decoding succeeded during receipt capture. Detail response includes:

```json
{
  "eta": {
    "verified": true,
    "uuid": "eta-receipt-uuid",
    "vendor_tax_reg": "123456789"
  }
}
```

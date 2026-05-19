# API Contract: Accountant Review Desk

**Primary base path**: `/api/v1/expenses`

All endpoints require Bearer JWT authentication. All responses are scoped by `company_id` from `get_tenant_scope`.

Role rules:
- Queue, detail, approve, reject, correct, bulk approve: `accountant` or `admin`
- AI metrics: `admin`
- Resubmit: original field worker or `admin`

---

## GET /api/v1/expenses/queue

Return a paginated review queue.

### Query Parameters

| Param | Type | Default | Constraints |
|-------|------|---------|-------------|
| `status` | string | `pending` | `pending`, `approved`, `rejected`, or `all` |
| `project_id` | string | none | UUID |
| `employee_id` | string | none | UUID of submitting user |
| `date_from` | string | none | ISO date/datetime, inclusive |
| `date_to` | string | none | ISO date/datetime, inclusive |
| `amount_min` | number | none | >= 0 |
| `amount_max` | number | none | >= amount_min |
| `sort_by` | string | `date` | `date`, `amount`, `project` |
| `sort_order` | string | `desc` | `asc`, `desc` |
| `page` | integer | `1` | >= 1 |
| `page_size` | integer | `25` | 1-100 |

### Response 200

```json
{
  "items": [
    {
      "id": "expense-uuid",
      "review_version": 3,
      "status": "pending",
      "amount": 1500.0,
      "currency": "EGP",
      "vendor": "Cement Egypt",
      "employee": {
        "id": "user-uuid",
        "name": "Ahmed Hassan",
        "name_ar": "Ahmed Hassan"
      },
      "project": {
        "id": "project-uuid",
        "name": "Tower A",
        "name_ar": "Tower A",
        "code": "TA"
      },
      "capture_mode": "combined",
      "created_at": "2026-05-16T20:30:00Z",
      "eta_verified": true,
      "confidence_summary": {
        "min": 0.91,
        "all_high": true,
        "low_count": 0
      },
      "anomaly_count": 0,
      "bulk_eligible": true
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 25,
  "pages": 2,
  "server_time": "2026-05-16T20:31:00Z"
}
```

---

## GET /api/v1/expenses/{expense_id}/review-detail

Return the full evidence package for review.

### Response 200

```json
{
  "id": "expense-uuid",
  "review_version": 3,
  "status": "pending",
  "amount": 1500.0,
  "currency": "EGP",
  "vendor": "Cement Egypt",
  "vendor_tax_reg": "123456789",
  "items": "Cement bags",
  "notes": "",
  "category_id": "category-uuid",
  "project_id": "project-uuid",
  "capture_mode": "combined",
  "receipt_url": "https://signed-r2-url",
  "voice_transcript": "Arabic transcript if present",
  "eta": {
    "verified": true,
    "uuid": "eta-receipt-uuid",
    "vendor_tax_reg": "123456789"
  },
  "ai_extraction": {
    "amount": 1500.0,
    "vendor": "Cement Egypt"
  },
  "ai_confidence": {
    "amount": 0.98,
    "vendor": 0.91,
    "items": 0.84
  },
  "anomaly_flags": {},
  "employee": {
    "id": "user-uuid",
    "name": "Ahmed Hassan",
    "name_ar": "Ahmed Hassan"
  },
  "audit_history": [
    {
      "id": "audit-uuid",
      "action_type": "correct",
      "actor_id": "accountant-uuid",
      "field_name": "vendor",
      "value_before": { "vendor": "Old" },
      "value_after": { "vendor": "New" },
      "created_at": "2026-05-16T20:31:00Z"
    }
  ],
  "created_at": "2026-05-16T20:30:00Z",
  "updated_at": "2026-05-16T20:31:00Z"
}
```

### Errors

- 403 if role is not accountant/admin
- 404 if the expense is outside the tenant or does not exist

---

## POST /api/v1/expenses/{expense_id}/approve

Approve one pending expense.

### Request

```json
{
  "review_version": 3
}
```

### Response 200

```json
{
  "id": "expense-uuid",
  "status": "approved",
  "review_version": 4,
  "reviewed_at": "2026-05-16T20:32:00Z",
  "next_pending_id": "next-expense-uuid"
}
```

### Errors

- 409 if `review_version` is stale or the expense is no longer pending

---

## POST /api/v1/expenses/{expense_id}/reject

Reject one pending expense. Rejection reason is required.

### Request

```json
{
  "review_version": 3,
  "reason": "Receipt is unreadable"
}
```

Validation:
- `reason` trimmed length must be >= 5
- max length 1000

### Response 200

```json
{
  "id": "expense-uuid",
  "status": "rejected",
  "review_version": 4,
  "rejection_reason": "Receipt is unreadable",
  "reviewed_at": "2026-05-16T20:32:00Z",
  "next_pending_id": "next-expense-uuid"
}
```

---

## POST /api/v1/expenses/{expense_id}/correct

Correct one editable field while the expense is pending.

### Request

```json
{
  "review_version": 3,
  "field_name": "vendor",
  "corrected_value": "Correct Vendor Name"
}
```

Allowed `field_name` values:
- `amount`
- `currency`
- `vendor`
- `vendor_tax_reg`
- `items`
- `category_id`
- `project_id`
- `notes`

### Response 200

```json
{
  "id": "expense-uuid",
  "review_version": 4,
  "field_name": "vendor",
  "value_before": "AI Vendor",
  "value_after": "Correct Vendor Name",
  "correction_feedback_created": true,
  "correction_feedback_id": "feedback-uuid"
}
```

Correction feedback is created only if the expense has an AI value for the field and the corrected value differs.

---

## POST /api/v1/expenses/bulk-approve

Approve multiple eligible expenses.

### Request

```json
{
  "items": [
    { "id": "expense-1", "review_version": 2 },
    { "id": "expense-2", "review_version": 5 }
  ]
}
```

Validation:
- max 50 items
- empty list returns approved count 0
- each ID is reloaded by tenant scope
- each expense must be pending, ETA verified, and all AI confidence values >= 0.8

### Response 200

```json
{
  "bulk_operation_id": "bulk-uuid",
  "approved": 2,
  "approved_ids": ["expense-1", "expense-2"],
  "skipped": [],
  "conflicts": []
}
```

Partial result example:

```json
{
  "bulk_operation_id": "bulk-uuid",
  "approved": 1,
  "approved_ids": ["expense-1"],
  "skipped": [
    {
      "id": "expense-2",
      "reason": "not_eligible"
    }
  ],
  "conflicts": [
    {
      "id": "expense-3",
      "reason": "stale_version"
    }
  ]
}
```

---

## POST /api/v1/expenses/{expense_id}/resubmit

Move a rejected expense back to pending on the same record after the field worker edits it.

### Request

```json
{
  "review_version": 4,
  "changes": {
    "amount": 1600.0,
    "receipt_url": "https://signed-r2-url"
  }
}
```

Rules:
- User must be the original submitter or admin.
- Current status must be `rejected`.
- Previous rejection reason remains in audit history and may remain on `expenses.rejection_reason` as latest rejection context.
- Status becomes `pending`; `review_version` increments.

### Response 200

```json
{
  "id": "expense-uuid",
  "status": "pending",
  "review_version": 5
}
```

---

## POST /api/v1/expenses/{expense_id}/receipt-url

Refresh a signed receipt image URL when the existing URL expires or fails.

### Response 200

```json
{
  "receipt_url": "https://signed-r2-url",
  "expires_in": 3600
}
```

Rules:
- Expense must belong to the current tenant.
- User must be accountant/admin, or the original submitter.
- Returns 404 if no receipt is attached.

---

## GET /api/v1/expenses/ai-metrics

Return company-scoped AI correction metrics. Admin only.

### Query Parameters

| Param | Type | Default |
|-------|------|---------|
| `date_from` | ISO date/datetime | none |
| `date_to` | ISO date/datetime | none |

### Response 200

```json
{
  "total_expenses": 1200,
  "total_ai_expenses": 875,
  "total_corrections": 96,
  "correction_rate": 0.1097,
  "corrections_by_field": [
    {
      "field_name": "vendor",
      "count": 42,
      "rate": 0.048
    },
    {
      "field_name": "amount",
      "count": 12,
      "rate": 0.0137
    }
  ],
  "daily_trend": [
    {
      "date": "2026-05-16",
      "corrections": 7,
      "ai_expenses": 64
    }
  ]
}
```

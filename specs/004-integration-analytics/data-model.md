# Data Model: Integration & Analytics

**Branch**: `004-integration-analytics` | **Date**: 2026-05-17

## New Entities

### IntegrationConfig

Company-level integration configuration. One record per company (upsert on change).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID (PK) | auto-generated | Primary key |
| company_id | UUID (FK → companies.id) | NOT NULL, UNIQUE | One integration per company |
| system_name | VARCHAR(50) | NOT NULL | e.g., "zoho_books", "odoo", "csv_daftra" |
| encrypted_credentials | TEXT | NOT NULL | AES-256-GCM encrypted JSON blob |
| oauth_refresh_token | TEXT | nullable | Encrypted refresh token (Zoho) |
| status | VARCHAR(20) | NOT NULL, default "pending" | pending / active / error / needs_reauth |
| last_sync_at | TIMESTAMP(tz) | nullable | Last successful export timestamp |
| last_error | TEXT | nullable | Most recent error message |
| field_mappings | JSONB | nullable | Project-to-account mappings, custom fields |
| created_at | TIMESTAMP(tz) | NOT NULL | auto |
| updated_at | TIMESTAMP(tz) | NOT NULL | auto |

**Indexes**:
- UNIQUE on `company_id` (enforces one-per-company)

**State transitions**: pending → active (after successful test) → error (on failure) → needs_reauth (credential expiry) → active (after re-auth)

---

### ExportRecord

Tracks every expense export attempt to an external system.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID (PK) | auto-generated | Primary key |
| company_id | UUID (FK → companies.id) | NOT NULL | Tenant scope |
| expense_id | UUID (FK → expenses.id) | NOT NULL | Which expense |
| system_name | VARCHAR(50) | NOT NULL | Target system at time of export |
| status | VARCHAR(30) | NOT NULL, default "pending" | pending / success / failed / cancelled_migration |
| external_ref_id | VARCHAR(255) | nullable | ID returned by external system |
| error_message | TEXT | nullable | Error details on failure |
| attempt_count | INTEGER | NOT NULL, default 0 | Number of attempts made |
| next_retry_at | TIMESTAMP(tz) | nullable | When to retry (null if not retrying) |
| created_at | TIMESTAMP(tz) | NOT NULL | First attempt time |
| updated_at | TIMESTAMP(tz) | NOT NULL | Last update |

**Indexes**:
- `ix_exports_company_status` on (company_id, status)
- `ix_exports_expense` on (expense_id)
- `ix_exports_retry` on (status, next_retry_at) WHERE status = 'failed'

**State transitions**: pending → success | failed → (retry) → success | failed (max 5) | cancelled_migration

**Uniqueness**: Combination of (expense_id, system_name) should have at most one non-cancelled record with status in (pending, success). This enforces idempotency.

---

## Modified Entities

### Expense (existing)

No schema changes needed. Uses existing fields:

| Field | Used For |
|-------|----------|
| `anomaly_flags` (JSONB) | Stores anomaly detection results (async populated within 30s) |
| `receipt_hash` (VARCHAR 64) | Perceptual hash for duplicate detection |
| `status` | Used to filter "approved" for analytics and ERP export |

**Anomaly flags JSONB structure**:
```json
{
  "duplicate_receipt": {
    "severity": "high",
    "message": "صورة إيصال مشابهة تم إرسالها سابقاً",
    "message_en": "Similar receipt image previously submitted",
    "similar_expense_id": "uuid-xxx",
    "similarity": 0.95
  },
  "statistical_outlier": {
    "severity": "medium",
    "message": "المبلغ أعلى بكثير من المعتاد لهذه الفئة",
    "message_en": "Amount significantly above average for this category",
    "avg": 125.0,
    "std": 18.5
  },
  "high_velocity": {
    "severity": "medium",
    "message": "3 مصروفات في آخر 10 دقائق",
    "message_en": "3 expenses in last 10 minutes"
  },
  "vendor_mismatch": {
    "severity": "low",
    "message": "هذا المورد عادة في فئة مختلفة",
    "message_en": "This vendor is usually in a different category",
    "expected_category": "materials",
    "actual_category": "transport"
  }
}
```

### Project (existing)

Verify `budget` field exists. If not, add:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| budget | NUMERIC(14,2) | nullable | Project budget for budget-vs-actual comparison |

---

## Relationships

```
Company 1──1 IntegrationConfig    (one integration per company)
Company 1──* ExportRecord         (many exports per company)
Expense 1──* ExportRecord         (one expense can have multiple export attempts)
Expense.anomaly_flags (JSONB)     (embedded, not a FK relationship)
```

## Migration Plan

1. Create `integration_configs` table
2. Create `export_records` table
3. Add `budget` column to `projects` table (if not present)
4. Add index on `expenses.receipt_hash` for duplicate detection: `ix_expenses_company_receipt_hash` on (company_id, receipt_hash)

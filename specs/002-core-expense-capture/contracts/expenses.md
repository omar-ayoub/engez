# API Contract: Expenses

**Base path**: `/api/v1/expenses`

---

## POST /api/v1/expenses

Submit a new expense. Used by the sync queue when submitting locally-saved expenses to the server.

### Authentication

Required. Bearer JWT token.

### Request

**Content-Type**: `application/json`

```json
{
  "offline_id": "local-uuid-123",
  "amount": 1500.00,
  "currency": "EGP",
  "vendor": "محل الأسمنت",
  "vendor_tax_reg": "123456789",
  "items": "أسمنت بورتلاند",
  "category_id": "cat-uuid-456",
  "project_id": "proj-uuid-789",
  "notes": "",
  "capture_mode": "voice",
  "voice_url": "https://r2.engez.app/comp-123/voice/2026-05/abc.webm",
  "voice_transcript": "دفعت ألف وخمسمية جنيه لمحل الأسمنت",
  "receipt_url": "https://r2.engez.app/comp-123/receipts/2026-05/def.jpg",
  "eta_uuid": "a1b2c3d4...",
  "eta_verified": true,
  "ai_extraction": { "...": "..." },
  "ai_confidence": { "amount": 0.95, "vendor": 0.90 }
}
```

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `offline_id` | string | Yes | UUID format | Client-generated ID for deduplication |
| `amount` | number | Yes | > 0, max 12 digits, 2 decimals | Expense amount |
| `currency` | string | No | 3-letter ISO code, default "EGP" | Currency code |
| `vendor` | string | Yes | Max 255 chars | Vendor name |
| `vendor_tax_reg` | string | No | Max 50 chars | Vendor tax registration from QR |
| `items` | string | Yes | Max 1000 chars | Description of what was purchased |
| `category_id` | string | No | UUID, must exist in categories table | Category reference |
| `project_id` | string | No | UUID, must exist in projects table | Project reference |
| `notes` | string | No | Max 2000 chars | Additional notes |
| `capture_mode` | string | Yes | `voice`/`receipt`/`combined`/`manual` | How the expense was captured |
| `voice_url` | string | No | Valid URL | R2 URL for archived voice recording |
| `voice_transcript` | string | No | Max 5000 chars | Voice transcription text |
| `receipt_url` | string | No | Valid URL | R2 URL for archived receipt image |
| `eta_uuid` | string | No | Max 64 chars | ETA e-invoice UUID |
| `eta_verified` | boolean | No | Default false | Whether ETA QR was decoded |
| `ai_extraction` | object | No | | Raw AI extraction output |
| `ai_confidence` | object | No | | Per-field confidence scores |

### Response — 201 Created

```json
{
  "id": "server-uuid-456",
  "offline_id": "local-uuid-123",
  "status": "pending",
  "synced_at": "2026-05-15T10:31:00Z",
  "created_at": "2026-05-15T10:30:00Z"
}
```

### Response — 409 Conflict

Returned when `offline_id` already exists (idempotent deduplication).

```json
{
  "detail": "تم إرسال هذا المصروف مسبقاً",
  "detail_en": "This expense was already submitted",
  "existing_id": "server-uuid-456"
}
```

### Deduplication

The `offline_id` field prevents duplicate submissions from the sync queue. If a POST arrives with an `offline_id` that already exists for the same company, return 409 with the existing server ID.

---

## GET /api/v1/expenses

List expenses for the current user's company. Supports pagination and filtering.

### Authentication

Required. Bearer JWT token.

### Query Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `status` | string | (all) | Filter by status: `draft`, `pending`, `synced`, `approved`, `rejected` |
| `capture_mode` | string | (all) | Filter by: `voice`, `receipt`, `combined`, `manual` |
| `from_date` | string | (none) | ISO date, inclusive |
| `to_date` | string | (none) | ISO date, inclusive |
| `project_id` | string | (none) | Filter by project UUID |
| `page` | int | 1 | Page number |
| `per_page` | int | 20 | Items per page (max 100) |

### Response — 200 OK

```json
{
  "items": [
    {
      "id": "server-uuid-456",
      "offline_id": "local-uuid-123",
      "amount": 1500.00,
      "currency": "EGP",
      "vendor": "محل الأسمنت",
      "items": "أسمنت بورتلاند",
      "category_id": "cat-uuid",
      "project_id": "proj-uuid",
      "capture_mode": "voice",
      "status": "synced",
      "eta_verified": true,
      "created_at": "2026-05-15T10:30:00Z",
      "synced_at": "2026-05-15T10:31:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 20,
  "pages": 3
}
```

---

## PATCH /api/v1/expenses/{id}

Update an existing expense. Used for corrections before approval.

### Authentication

Required. Bearer JWT token. User must own the expense or be admin.

### Request

**Content-Type**: `application/json`

Any subset of the POST fields (except `offline_id` and `capture_mode`).

```json
{
  "amount": 1600.00,
  "vendor": "محل الأسمنت المعدل"
}
```

### Response — 200 OK

```json
{
  "id": "server-uuid-456",
  "status": "pending",
  "updated_at": "2026-05-15T11:00:00Z"
}
```

### Correction Feedback

When a PATCH modifies a field that was AI-extracted (voice or receipt capture mode), the backend automatically creates a CorrectionFeedback record if the new value differs from the `ai_extraction` value for that field. This feeds the compounding moat.

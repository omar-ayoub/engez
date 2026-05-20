# Data Model: Core Expense Capture

**Phase**: 1 — Design & Contracts | **Date**: 2026-05-15

## Schema Changes from Phase 1

### PostgreSQL — Expense Table Updates

The `expenses` table (created in Phase 1) needs three new columns and one constraint change:

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `items` | `TEXT` | NOT NULL | `''` | Description of what was purchased. Required per clarification. Existing rows get empty string default. |
| `capture_mode` | `VARCHAR(20)` | NOT NULL | `'manual'` | Enum: `voice`, `receipt`, `combined`, `manual`. Tracks how the expense was captured. |
| `voice_url` | `VARCHAR(500)` | YES | NULL | Cloudflare R2 signed URL for the voice recording blob. |

**Constraint change**: `category_id` changes from NOT NULL to NULLABLE. Per clarification, category is optional for submission. Existing rows retain their category_id values.

**Migration**: Single Alembic migration `add_capture_fields` that:
1. Adds `items` column with server_default `''`
2. Adds `capture_mode` column with server_default `'manual'`
3. Adds `voice_url` column (nullable)
4. Alters `category_id` to allow NULL

### PostgreSQL — No New Tables

All entities needed (Expense, VendorCache, CorrectionFeedback, Category, Project) already exist from Phase 1. No new tables are required.

---

## Entity Updates

### Expense (updated)

```
Expense
├── id: UUID (PK)
├── company_id: UUID (FK → companies, NOT NULL) [TenantMixin]
├── user_id: UUID (FK → users, NOT NULL)
├── project_id: UUID (FK → projects, nullable) [optional]
├── category_id: UUID (FK → categories, nullable) [was NOT NULL, now optional]
├── amount: DECIMAL(12,2) (NOT NULL) [required]
├── currency: VARCHAR(3) (NOT NULL, default 'EGP')
├── vendor: VARCHAR(255) (nullable) [required at app level, but DB allows null for drafts]
├── vendor_tax_reg: VARCHAR(50) (nullable) [from ETA QR decode]
├── items: TEXT (NOT NULL, default '') [NEW — required field per clarification]
├── notes: TEXT (nullable) [optional]
├── capture_mode: VARCHAR(20) (NOT NULL, default 'manual') [NEW — voice/receipt/combined/manual]
├── receipt_url: VARCHAR(500) (nullable) [R2 URL for receipt image]
├── receipt_hash: VARCHAR(64) (nullable) [SHA-256 of original receipt]
├── voice_url: VARCHAR(500) (nullable) [NEW — R2 URL for voice recording]
├── voice_transcript: TEXT (nullable) [transcription from Whisper]
├── status: VARCHAR(20) (NOT NULL, default 'pending')
│   └── States: draft → pending → synced → approved → rejected
├── rejection_reason: TEXT (nullable)
├── eta_uuid: VARCHAR(64) (nullable) [ETA e-invoice UUID]
├── eta_verified: BOOLEAN (default false)
├── ai_extraction: JSONB (nullable) [raw AI extraction output]
├── ai_confidence: JSONB (nullable) [field-level confidence scores]
├── anomaly_flags: JSONB (nullable) [for Phase 3 review desk]
├── offline_id: VARCHAR(36) (nullable) [client-generated UUID for dedup]
├── synced_at: TIMESTAMPTZ (nullable)
├── created_at: TIMESTAMPTZ (NOT NULL) [TimestampMixin]
└── updated_at: TIMESTAMPTZ (NOT NULL) [TimestampMixin]
```

**Indexes** (existing, unchanged):
- `ix_expenses_company_status` → (company_id, status)
- `ix_expenses_company_project` → (company_id, project_id)
- `ix_expenses_user_created` → (user_id, created_at)

### VendorCache (unchanged from Phase 1)

```
VendorCache
├── id: UUID (PK)
├── company_id: UUID (FK → companies, NOT NULL) [TenantMixin]
├── tax_registration: VARCHAR(50) (NOT NULL, indexed)
├── name: VARCHAR(255) (NOT NULL) [English/transliterated name]
├── name_ar: VARCHAR(255) (nullable) [Arabic name]
├── category_hint: VARCHAR(100) (nullable) [default category for this vendor]
├── created_at: TIMESTAMPTZ [TimestampMixin]
└── updated_at: TIMESTAMPTZ [TimestampMixin]

Unique constraint: (company_id, tax_registration)
```

### CorrectionFeedback (unchanged from Phase 1)

```
CorrectionFeedback
├── id: UUID (PK)
├── company_id: UUID (FK → companies, NOT NULL) [TenantMixin]
├── expense_id: UUID (FK → expenses, NOT NULL)
├── field_name: VARCHAR(50) (NOT NULL) [amount, vendor, category, etc.]
├── ai_value: TEXT (NOT NULL) [what AI extracted]
├── corrected_value: TEXT (NOT NULL) [what user corrected to]
├── corrected_by: UUID (FK → users, NOT NULL)
├── created_at: TIMESTAMPTZ [TimestampMixin]
└── updated_at: TIMESTAMPTZ [TimestampMixin]
```

---

## Expense Status State Machine

```
                    ┌──────────────────────────────────┐
                    │                                  │
                    ▼                                  │
  [capture] ──→ DRAFT ──→ PENDING ──→ SYNCED ──→ APPROVED
                  │          │                     │
                  │          │                     ▼
                  │          └──────────────→ REJECTED
                  │
                  └──→ (discard — deleted from local DB)
```

**State transitions**:
- `draft`: Initial state for all new expenses. Auto-saved locally.
  - For manual capture: transitions to `pending` on submit.
  - For voice/receipt capture (online): AI extraction pre-fills form, transitions to `pending` on submit.
  - For voice/receipt capture (offline): stays as `draft` until AI processing completes and user confirms.
- `pending`: User has submitted. Queued for server sync.
- `synced`: Successfully synced to the server.
- `approved`: Approved by accountant (Phase 3).
- `rejected`: Rejected by accountant with reason (Phase 3).

**Offline-specific flow**:
1. Offline voice/receipt capture → `draft` (with blobs in IndexedDB)
2. Connectivity returns → blobs uploaded for AI processing → extraction stored locally
3. User reviews draft → confirms → `pending`
4. Sync queue sends to server → `synced`

---

## IndexedDB Schema (Dexie.js) — Version 2

### OfflineExpense Interface (updated)

```typescript
export interface OfflineExpense {
  id: string;
  userId: string;
  projectId?: string;
  categoryId?: string;          // Changed: now optional (was required)
  amount: number;
  currency: string;
  vendor?: string;
  vendorTaxReg?: string;
  items: string;                // NEW: required field
  notes?: string;
  captureMode: "voice" | "receipt" | "combined" | "manual";  // NEW
  receiptBlob?: Blob;
  receiptUrl?: string;
  voiceBlob?: Blob;
  voiceUrl?: string;            // NEW: R2 URL after upload
  voiceTranscript?: string;
  status: "draft" | "pending" | "synced" | "approved" | "rejected";
  etaUuid?: string;
  etaVerified: boolean;
  aiExtraction?: Record<string, unknown>;
  aiConfidence?: Record<string, unknown>;
  draftProcessed: boolean;      // NEW: true when AI has processed offline blobs
  createdAt: Date;
  syncedAt?: Date;
  syncError?: string;
}
```

### New: OfflineVendor Interface

```typescript
export interface OfflineVendor {
  id: string;
  companyId: string;
  name: string;
  nameAr?: string;
  taxRegistration?: string;
  categoryHint?: string;
}
```

### Dexie Schema v2

```typescript
db.version(2).stores({
  expenses: "id, userId, projectId, categoryId, status, captureMode, createdAt, syncedAt",
  projects: "id, companyId, code, isActive",
  categories: "id, companyId, isActive",
  syncQueue: "id, type, createdAt, retryCount",
  vendorCache: "id, companyId, name, nameAr, taxRegistration",  // NEW table
}).upgrade(tx => {
  return tx.table('expenses').toCollection().modify(expense => {
    expense.captureMode = expense.captureMode || 'manual';
    expense.items = expense.items || '';
    expense.draftProcessed = expense.draftProcessed ?? false;
  });
});
```

**Key changes from v1**:
1. `expenses` table: added `captureMode` index
2. New `vendorCache` table for offline vendor autocomplete
3. Upgrade function migrates existing expenses with default values

---

## AI Extraction Data Shapes

### Voice Extraction Response (stored in `ai_extraction`)

```json
{
  "source": "voice",
  "transcript": "دفعت ألف وخمسمية جنيه لمحل الأسمنت في موقع المعادي",
  "amount": 1500,
  "currency": "EGP",
  "category": "materials",
  "vendor": "محل الأسمنت",
  "items": "أسمنت",
  "project_hint": "موقع المعادي",
  "confidence": {
    "amount": 0.95,
    "category": 0.80,
    "vendor": 0.90,
    "items": 0.85,
    "project_hint": 0.70
  }
}
```

### Receipt Extraction Response (stored in `ai_extraction`)

```json
{
  "source": "receipt",
  "amount": 1500.00,
  "currency": "EGP",
  "vendor": "محل الأسمنت للتوريدات",
  "vendor_tax_reg": "123456789",
  "date": "2026-05-15",
  "category": "materials",
  "items": "أسمنت بورتلاند 10 شكاير",
  "line_items": [
    { "description": "أسمنت بورتلاند", "quantity": 10, "amount": 1500.00 }
  ],
  "qr_detected": true,
  "qr_data": {
    "uuid": "a1b2c3d4...",
    "total": 1500.00,
    "issuer_rin": "123456789",
    "datetime": "2026-05-15T10:30:00Z"
  },
  "confidence": {
    "amount": 0.99,
    "vendor": 0.92,
    "date": 0.95,
    "category": 0.75,
    "items": 0.88
  }
}
```

### Combined Extraction (merged client-side)

Priority: QR data > Receipt OCR > Voice extraction

```json
{
  "source": "combined",
  "amount": 1500.00,
  "amount_source": "qr",
  "vendor": "محل الأسمنت للتوريدات",
  "vendor_source": "receipt_ocr",
  "items": "أسمنت بورتلاند 10 شكاير",
  "items_source": "receipt_ocr",
  "category": "materials",
  "category_source": "voice",
  "project_hint": "موقع المعادي",
  "project_hint_source": "voice"
}
```

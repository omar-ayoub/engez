# Data Model: Phase 1 — Foundation

**Date**: 2026-05-15

## Entity Relationship Overview

```
Company 1──* User
Company 1──* Project
Company 1──* Category
Company 1──* Expense
Company 1──* CorrectionFeedback
Company 1──* VendorCache

User    1──* Expense          (user_id)
User    1──* CorrectionFeedback (corrected_by)
Project 0..1──* Expense       (project_id, optional)
Category 1──* Expense         (category_id)
Expense 1──* CorrectionFeedback (expense_id)
```

## Entities

### Company

The root tenant entity. Not scoped to a company_id (it *is* the tenant).

| Field | Type | Constraints | Notes |
| ----- | ---- | ----------- | ----- |
| id | UUID (string 36) | PK | Server-generated |
| name | string 255 | NOT NULL | English name |
| name_ar | string 255 | NOT NULL | Arabic name |
| tax_registration | string 50 | NULLABLE | Egyptian tax reg number |
| is_active | boolean | DEFAULT true | Deactivated companies block new logins |
| settings | JSONB | DEFAULT {} | Company-level config (future use) |
| created_at | timestamptz | DEFAULT now() | |
| updated_at | timestamptz | DEFAULT now() | Auto-updated |

### User

A person within a company. Email is globally unique.

| Field | Type | Constraints | Notes |
| ----- | ---- | ----------- | ----- |
| id | UUID (string 36) | PK | Server-generated |
| company_id | UUID (string 36) | FK → companies.id, NOT NULL, INDEX | Tenant scope |
| email | string 255 | UNIQUE, NOT NULL | Global uniqueness |
| name | string 255 | NOT NULL | English name |
| name_ar | string 255 | NOT NULL | Arabic name |
| hashed_password | string 255 | NOT NULL | bcrypt hash |
| role | string 20 | NOT NULL, DEFAULT 'field_worker' | field_worker, accountant, admin |
| is_active | boolean | DEFAULT true | Soft delete |
| failed_login_attempts | integer | DEFAULT 0 | Reset on successful login |
| locked_until | timestamptz | NULLABLE | Set on 5th failed attempt (now + 15min) |
| push_subscription | JSONB | NULLABLE | Web Push subscription object |
| webauthn_credential_id | string 255 | NULLABLE | WebAuthn credential for biometric |
| webauthn_public_key | text | NULLABLE | WebAuthn public key (CBOR-encoded) |
| created_at | timestamptz | DEFAULT now() | |
| updated_at | timestamptz | DEFAULT now() | Auto-updated |

**State transitions**:
- Login attempt → increment `failed_login_attempts` on failure, reset to 0 on success
- 5th failure → set `locked_until` = now + 15 minutes
- Login while locked → reject with calm message, no increment
- Lock expired (`locked_until < now()`) → treat as unlocked, reset counter on next success

### Project

A cost center within a company.

| Field | Type | Constraints | Notes |
| ----- | ---- | ----------- | ----- |
| id | UUID (string 36) | PK | Server-generated |
| company_id | UUID (string 36) | FK → companies.id, NOT NULL, INDEX | Tenant scope |
| name | string 255 | NOT NULL | English name |
| name_ar | string 255 | NOT NULL | Arabic name |
| code | string 50 | NOT NULL | Short code (e.g., "PROJ-001") |
| budget | numeric 15,2 | NULLABLE | Optional budget cap |
| is_active | boolean | DEFAULT true | Inactive projects hidden from field workers |
| created_at | timestamptz | DEFAULT now() | |
| updated_at | timestamptz | DEFAULT now() | Auto-updated |

**Unique constraint**: `(company_id, code)` — project codes unique within a company.

### Category

Admin-defined expense classification. Per-company.

| Field | Type | Constraints | Notes |
| ----- | ---- | ----------- | ----- |
| id | UUID (string 36) | PK | Server-generated |
| company_id | UUID (string 36) | FK → companies.id, NOT NULL, INDEX | Tenant scope |
| name | string 100 | NOT NULL | English name |
| name_ar | string 100 | NOT NULL | Arabic name |
| sort_order | integer | DEFAULT 0 | Display ordering |
| is_active | boolean | DEFAULT true | Inactive categories hidden from field workers |
| created_at | timestamptz | DEFAULT now() | |
| updated_at | timestamptz | DEFAULT now() | Auto-updated |

**Unique constraint**: `(company_id, name)` — category names unique within a company.

### Expense

The core business record. Created client-side (offline-capable).

| Field | Type | Constraints | Notes |
| ----- | ---- | ----------- | ----- |
| id | UUID (string 36) | PK | Client-generated (offline support) |
| company_id | UUID (string 36) | FK → companies.id, NOT NULL, INDEX | Tenant scope |
| user_id | UUID (string 36) | FK → users.id, NOT NULL | Who submitted |
| project_id | UUID (string 36) | FK → projects.id, NULLABLE | Optional project link |
| category_id | UUID (string 36) | FK → categories.id, NOT NULL | From predefined list |
| amount | numeric 12,2 | NOT NULL | Expense amount |
| currency | string 3 | NOT NULL, DEFAULT 'EGP' | ISO 4217 |
| vendor | string 255 | NULLABLE | Vendor name |
| vendor_tax_reg | string 50 | NULLABLE | Vendor tax registration |
| notes | text | NULLABLE | Free-text notes |
| receipt_url | string 500 | NULLABLE | R2 signed URL |
| receipt_hash | string 64 | NULLABLE | SHA-256 for duplicate detection |
| voice_transcript | text | NULLABLE | Whisper transcription |
| status | string 20 | NOT NULL, DEFAULT 'pending' | pending, approved, rejected |
| rejection_reason | text | NULLABLE | Set on rejection |
| eta_uuid | string 64 | NULLABLE | Egyptian Tax Authority invoice UUID |
| eta_verified | boolean | DEFAULT false | ETA verification status |
| ai_extraction | JSONB | NULLABLE | Raw AI OCR output |
| ai_confidence | JSONB | NULLABLE | Per-field confidence scores |
| anomaly_flags | JSONB | NULLABLE | Detected anomalies |
| synced_at | timestamptz | NULLABLE | When synced from client |
| offline_id | string 36 | NULLABLE | Original client-side ID |
| created_at | timestamptz | DEFAULT now() | |
| updated_at | timestamptz | DEFAULT now() | Auto-updated |

**Indexes**:
- `(company_id, status)` — accountant review queue
- `(company_id, project_id)` — project expense listing
- `(user_id, created_at)` — user's expense history

**State transitions**: `pending` → `approved` | `rejected`. No reverse transitions in Phase 1.

### CorrectionFeedback

Records accountant corrections to AI-extracted fields. The compounding data moat.

| Field | Type | Constraints | Notes |
| ----- | ---- | ----------- | ----- |
| id | UUID (string 36) | PK | Server-generated |
| company_id | UUID (string 36) | FK → companies.id, NOT NULL, INDEX | Tenant scope |
| expense_id | UUID (string 36) | FK → expenses.id, NOT NULL | Which expense |
| field_name | string 50 | NOT NULL | Which field was corrected |
| ai_value | text | NOT NULL | What AI extracted |
| corrected_value | text | NOT NULL | What accountant corrected to |
| corrected_by | UUID (string 36) | FK → users.id, NOT NULL | Who corrected |
| created_at | timestamptz | DEFAULT now() | |
| updated_at | timestamptz | DEFAULT now() | Auto-updated |

### VendorCache

Accelerates future submissions by caching vendor info by tax registration.

| Field | Type | Constraints | Notes |
| ----- | ---- | ----------- | ----- |
| id | UUID (string 36) | PK | Server-generated |
| company_id | UUID (string 36) | FK → companies.id, NOT NULL, INDEX | Tenant scope |
| tax_registration | string 50 | NOT NULL, INDEX | Lookup key |
| name | string 255 | NOT NULL | English name |
| name_ar | string 255 | NULLABLE | Arabic name |
| category_hint | string 100 | NULLABLE | Suggested category |
| created_at | timestamptz | DEFAULT now() | |
| updated_at | timestamptz | DEFAULT now() | Auto-updated |

**Unique constraint**: `(company_id, tax_registration)` — one vendor per tax reg per company.

## Client-Side Schema (Dexie.js / IndexedDB)

Mirrors the server schema for offline operation.

### OfflineExpense

```
id mod userId mod projectId mod categoryId mod amount mod currency mod
category mod vendor mod vendorTaxReg mod notes mod receiptBlob mod
receiptUrl mod voiceBlob mod voiceTranscript mod
status (draft|pending|synced|approved|rejected) mod
etaUuid mod etaVerified mod aiExtraction mod aiConfidence mod
createdAt mod syncedAt mod syncError
```

**Dexie indexes**: `id, userId, projectId, categoryId, status, createdAt, syncedAt`

### OfflineProject

```
id mod companyId mod name mod nameAr mod code mod budget mod isActive
```

**Dexie indexes**: `id, companyId, code, isActive`

### OfflineCategory

```
id mod companyId mod name mod nameAr mod sortOrder mod isActive
```

**Dexie indexes**: `id, companyId, isActive`

### SyncQueue

```
id mod type (expense|expense_update) mod payload (JSON string) mod
retryCount mod createdAt mod lastAttempt
```

**Dexie indexes**: `id, type, createdAt, retryCount`

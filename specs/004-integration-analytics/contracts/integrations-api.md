# API Contract: Integrations

**Base path**: `/api/v1/integrations`
**Auth**: Bearer JWT (role: admin or accountant)

---

## GET /available

List available integration systems.

**Response** `200`:
```json
[
  {
    "system_name": "zoho_books",
    "display_name": "Zoho Books",
    "display_name_ar": "زوهو بوكس",
    "required_fields": ["access_token", "organization_id", "expense_account_id"]
  }
]
```

---

## POST /configure

Configure or update the company's integration.

**Request**:
```json
{
  "system_name": "zoho_books",
  "credentials": {
    "access_token": "...",
    "organization_id": "...",
    "expense_account_id": "..."
  },
  "field_mappings": {
    "project_mapping": { "proj-001": "zoho-proj-id" }
  }
}
```

**Response** `201`:
```json
{
  "system_name": "zoho_books",
  "status": "active",
  "last_sync_at": null
}
```

**Errors**: `422` invalid system_name, `403` insufficient role

---

## POST /test-connection

Test credentials without saving.

**Request**: Same as `/configure`

**Response** `200`:
```json
{
  "success": true,
  "message": "Connection successful"
}
```

**Error Response** `200`:
```json
{
  "success": false,
  "message": "Invalid organization ID"
}
```

---

## GET /status

Get current integration status for the company.

**Response** `200` (configured):
```json
{
  "configured": true,
  "system_name": "zoho_books",
  "status": "active",
  "last_sync_at": "2026-05-16T10:00:00Z",
  "last_error": null
}
```

**Response** `200` (not configured):
```json
{
  "configured": false
}
```

---

## POST /export/{expense_id}

Manually trigger export for a single expense.

**Response** `202`:
```json
{
  "export_id": "uuid",
  "status": "pending"
}
```

**Errors**: `404` expense not found, `409` already exported, `400` expense not approved

---

## POST /export/{expense_id}/retry

Retry a failed export.

**Response** `202`:
```json
{
  "export_id": "uuid",
  "status": "pending",
  "attempt_count": 2
}
```

---

## GET /exports

List export records with filtering.

**Query params**: `status` (all/pending/success/failed), `page`, `page_size`

**Response** `200`:
```json
{
  "items": [
    {
      "id": "uuid",
      "expense_id": "uuid",
      "system_name": "zoho_books",
      "status": "success",
      "external_ref_id": "zoho-123",
      "attempt_count": 1,
      "created_at": "2026-05-16T10:00:00Z"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 25
}
```

---

## GET /csv-export

Download CSV file for Daftra import.

**Query params**: `date_from` (required), `date_to` (required)

**Response** `200`: `Content-Type: text/csv` with file download

**Errors**: `422` missing date params

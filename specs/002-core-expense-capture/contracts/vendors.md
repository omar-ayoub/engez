# API Contract: Vendors

**Base path**: `/api/v1/vendors`

---

## GET /api/v1/vendors

Fetch the full vendor cache for the current user's company. Used by the client to populate the local Dexie vendorCache table for offline autocomplete.

### Authentication

Required. Bearer JWT token.

### Response — 200 OK

```json
{
  "vendors": [
    {
      "id": "v-uuid-123",
      "name": "Cement Supply Co",
      "name_ar": "محل الأسمنت للتوريدات",
      "tax_registration": "123456789",
      "category_hint": "materials"
    },
    {
      "id": "v-uuid-456",
      "name": "Abu Ali Kiosk",
      "name_ar": "كشك أبو علي",
      "tax_registration": null,
      "category_hint": "food"
    }
  ],
  "total": 2,
  "last_updated": "2026-05-15T10:00:00Z"
}
```

### Sync Strategy

The client calls this endpoint:
1. On login (full sync)
2. Every 15 minutes when online (incremental — uses `If-Modified-Since` header)

The response is stored in the Dexie `vendorCache` table via `bulkPut` (upsert).

---

## GET /api/v1/vendors/search

Server-side vendor search. Used as a fallback when the local cache is empty or for admin interfaces.

### Authentication

Required. Bearer JWT token.

### Query Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `q` | string | (required) | Search query (min 2 chars). Matches name, name_ar, tax_registration |
| `limit` | int | 10 | Max results (max 50) |

### Response — 200 OK

```json
{
  "vendors": [
    {
      "id": "v-uuid-123",
      "name": "Cement Supply Co",
      "name_ar": "محل الأسمنت للتوريدات",
      "tax_registration": "123456789",
      "category_hint": "materials"
    }
  ]
}
```

### Note on Autocomplete

Primary autocomplete happens locally via Dexie (offline-capable). This server endpoint exists for:
- Initial population when the client has no cached vendors
- Admin vendor management (Phase 3)
- Fallback when local search returns no results and the device is online

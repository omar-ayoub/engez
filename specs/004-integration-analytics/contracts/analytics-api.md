# API Contract: Analytics

**Base path**: `/api/v1/analytics`
**Auth**: Bearer JWT (role: admin or accountant)

---

## GET /spend-by-project

Spend breakdown by project for a time period.

**Query params**: `days` (int, 7-365, default 30)

**Response** `200`:
```json
[
  {
    "name": "Tower A",
    "name_ar": "برج أ",
    "budget": 50000.00,
    "total_spend": 35000.00,
    "expense_count": 42
  }
]
```

---

## GET /spend-by-category

Spend breakdown by category.

**Query params**: `days` (int, default 30)

**Response** `200`:
```json
[
  {
    "category": "materials",
    "category_ar": "مواد",
    "total": 45000.00,
    "count": 55
  }
]
```

---

## GET /spend-trend

Weekly spend trend.

**Query params**: `days` (int, 7-365, default 90)

**Response** `200`:
```json
[
  {
    "week": "2026-04-07",
    "total": 12000.00,
    "count": 15
  }
]
```

---

## GET /budget-vs-actual

Budget comparison for active projects.

**Response** `200`:
```json
[
  {
    "name": "Tower A",
    "name_ar": "برج أ",
    "budget": 50000.00,
    "actual_spend": 35000.00
  }
]
```

---

## GET /summary

Dashboard summary KPIs.

**Query params**: `days` (int, default 30)

**Response** `200`:
```json
{
  "total_spend": 71000.00,
  "expense_count": 88,
  "project_count": 3,
  "period_days": 30
}
```

---

## GET /export

Export analytics data as file download.

**Query params**:
- `format`: "csv" | "excel" (required)
- `view`: "spend-by-project" | "spend-by-category" | "spend-trend" | "budget-vs-actual" (required)
- `days`: int (default 30)

**Response** `200`:
- CSV: `Content-Type: text/csv`
- Excel: `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

**Errors**: `422` invalid format or view

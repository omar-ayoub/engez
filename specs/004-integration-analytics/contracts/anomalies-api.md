# API Contract: Anomaly Detection

**Base path**: `/api/v1`
**Auth**: Bearer JWT

---

## POST /expenses/check-anomalies

Run anomaly detection checks against expense data. Used internally after expense submission (background task) and for testing.

**Auth**: admin or accountant role

**Request**:
```json
{
  "amount": 500.0,
  "currency": "EGP",
  "vendor": "Test Vendor",
  "items": "Office supplies",
  "capture_mode": "receipt",
  "category_id": "cat-001",
  "receipt_hash": "abc123def456",
  "user_id": "user-001",
  "check_velocity": true
}
```

**Response** `200`:
```json
{
  "flags": [
    {
      "type": "statistical_outlier",
      "severity": "medium",
      "message": "المبلغ أعلى بكثير من المعتاد لهذه الفئة",
      "message_en": "Amount significantly above average for this category",
      "metadata": {
        "avg": 125.0,
        "std": 18.5
      }
    },
    {
      "type": "duplicate_receipt",
      "severity": "high",
      "message": "صورة إيصال مشابهة تم إرسالها سابقاً",
      "message_en": "Similar receipt image previously submitted",
      "metadata": {
        "similar_expense_id": "exp-001",
        "similarity": 0.95
      }
    }
  ],
  "blocking": false
}
```

**Notes**: `blocking` is always `false` — anomaly flags are advisory only.

---

## GET /anomalies/metrics

Admin-only view of anomaly detection performance metrics.

**Auth**: admin role only

**Query params**: `days` (int, default 30)

**Response** `200`:
```json
{
  "total_flags": 24,
  "by_type": {
    "duplicate_receipt": 5,
    "statistical_outlier": 8,
    "high_velocity": 7,
    "vendor_mismatch": 4
  },
  "avg_flags_per_expense": 0.12,
  "rejection_correlation": 0.65,
  "period_days": 30
}
```

**Errors**: `403` non-admin user

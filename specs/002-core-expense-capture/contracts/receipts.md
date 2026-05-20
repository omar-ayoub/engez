# API Contract: Receipt Capture

**Base path**: `/api/v1/receipts`

---

## POST /api/v1/receipts/extract

Extract text from a receipt image using AI vision OCR and decode ETA QR codes.

### Authentication

Required. Bearer JWT token. User must be active with an active company.

### Rate Limiting

100 requests per company per hour (Redis sliding window).

### Request

**Content-Type**: `multipart/form-data`

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `image` | File | Yes | Max 10MB, image/* MIME type | Compressed receipt photo (JPEG preferred, client-compressed to ~300KB) |

### Response — 200 OK

```json
{
  "extraction": {
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
    "confidence": {
      "amount": 0.98,
      "currency": 1.0,
      "vendor": 0.92,
      "date": 0.95,
      "category": 0.75,
      "items": 0.88
    }
  },
  "qr_detected": true,
  "qr_data": {
    "uuid": "a1b2c3d4e5f6...",
    "total": 1500.00,
    "issuer_rin": "123456789",
    "datetime": "2026-05-15T10:30:00Z"
  },
  "receipt_url": "https://r2.engez.app/comp-123/receipts/2026-05/ghi-jkl.jpg"
}
```

**Field notes**:
- `extraction`: Merged result. When `qr_detected` is true, QR values override OCR values for `amount`, `vendor_tax_reg`, and `date`.
- `extraction.vendor_tax_reg`: Present only when QR decoded or OCR detects a tax registration number.
- `extraction.line_items`: Array of line items visible on the receipt. May be empty if not discernible.
- `qr_data`: Raw ETA QR decode output. `null` if no QR code detected.
- `receipt_url`: R2 signed URL where the receipt image is archived. Valid for 1 hour.

### Response — 200 OK (no QR detected)

```json
{
  "extraction": {
    "amount": 350.00,
    "currency": "EGP",
    "vendor": "كشك أبو علي",
    "date": "2026-05-15",
    "category": "food",
    "items": "غداء عمال",
    "line_items": [],
    "confidence": {
      "amount": 0.70,
      "vendor": 0.60,
      "date": 0.85,
      "category": 0.55,
      "items": 0.50
    }
  },
  "qr_detected": false,
  "qr_data": null,
  "receipt_url": "https://r2.engez.app/comp-123/receipts/2026-05/xyz.jpg"
}
```

### Response — 413 Payload Too Large

```json
{
  "detail": "ملف الصورة كبير جداً (الحد الأقصى 10 ميجابايت)",
  "detail_en": "Image file too large (max 10MB)"
}
```

### Response — 422 Unprocessable Entity

```json
{
  "detail": "تعذر قراءة الإيصال. يرجى إعادة التصوير",
  "detail_en": "Could not read receipt. Please retake the photo",
  "extraction": null,
  "qr_detected": false
}
```

### Response — 429 Too Many Requests

```json
{
  "detail": "تم تجاوز حد الاستخدام. يرجى المحاولة لاحقاً",
  "detail_en": "Rate limit exceeded. Please try again later",
  "retry_after": 3600
}
```

### Behavior

1. Validate file size (max 10MB) and MIME type (image/*).
2. Upload image to Cloudflare R2 (`{company_id}/receipts/{YYYY-MM}/{uuid}.jpg`).
3. Attempt ETA QR decode (pyzbar): original image, then grayscale+contrast-enhanced fallback.
4. Send image to GPT-4o vision with receipt OCR prompt (Arabic/English, thermal receipt aware).
5. Merge QR data with OCR extraction (QR overrides for amount, tax_reg, date).
6. If QR vendor tax_reg found, look up vendor name/category from VendorCache.
7. Return merged extraction, QR status, and R2 URL.

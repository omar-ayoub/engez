# API Contract: Voice Capture

**Base path**: `/api/v1/voice`

---

## POST /api/v1/voice/extract

Transcribe an Egyptian Arabic voice recording and extract structured expense data.

### Authentication

Required. Bearer JWT token. User must be active with an active company.

### Rate Limiting

100 requests per company per hour (Redis sliding window).

### Request

**Content-Type**: `multipart/form-data`

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `audio` | File | Yes | Max 10MB, audio/* MIME type | Voice recording blob (webm/opus or mp4/aac) |

### Response — 200 OK

```json
{
  "transcript": "دفعت ألف وخمسمية جنيه لمحل الأسمنت في موقع المعادي",
  "extraction": {
    "amount": 1500,
    "currency": "EGP",
    "category": "materials",
    "vendor": "محل الأسمنت",
    "items": "أسمنت",
    "project_hint": "موقع المعادي",
    "confidence": {
      "amount": 0.95,
      "currency": 1.0,
      "category": 0.80,
      "vendor": 0.90,
      "items": 0.85,
      "project_hint": 0.70
    }
  },
  "voice_url": "https://r2.engez.app/comp-123/voice/2026-05/abc-def.webm"
}
```

**Field notes**:
- `transcript`: Raw transcription text from gpt-4o-mini-transcribe.
- `extraction.amount`: `null` if amount cannot be determined (never guessed).
- `extraction.confidence`: 0-1 score per field. Used by UI for highlighting.
- `voice_url`: R2 signed URL where the recording is archived. Valid for 1 hour.

### Response — 413 Payload Too Large

```json
{
  "detail": "ملف الصوت كبير جداً (الحد الأقصى 10 ميجابايت)",
  "detail_en": "Audio file too large (max 10MB)"
}
```

### Response — 422 Unprocessable Entity

Returned when audio cannot be transcribed (corrupted file, no speech detected).

```json
{
  "detail": "تعذر معالجة التسجيل الصوتي",
  "detail_en": "Could not process voice recording",
  "extraction": null,
  "transcript": null
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

1. Validate file size (max 10MB) and MIME type (audio/*).
2. Upload audio blob to Cloudflare R2 (`{company_id}/voice/{YYYY-MM}/{uuid}.{ext}`).
3. Send audio to gpt-4o-mini-transcribe with Egyptian Arabic domain prompt.
4. Fetch up to 10 recent correction_feedback records for the company.
5. Send transcript + few-shot examples to gpt-4o-mini for structured JSON extraction.
6. Return transcript, extraction with confidence scores, and R2 URL.

### Performance Target

< 5 seconds end-to-end under normal network conditions (SC-011).

# API Contract: Web Push Notifications

**Base path**: `/api/v1/notifications`

All endpoints require Bearer JWT authentication and tenant scoping.

## GET /api/v1/notifications/vapid-public-key

Return the public VAPID key used by the browser Push API.

### Response 200

```json
{
  "public_key": "base64url-vapid-public-key"
}
```

### Errors

- 503 if VAPID is not configured in this environment

---

## PUT /api/v1/notifications/subscription

Create or replace the current user's push subscription.

### Request

```json
{
  "endpoint": "https://push.service/send/abc",
  "expirationTime": null,
  "keys": {
    "p256dh": "base64url-public-key",
    "auth": "base64url-auth-secret"
  }
}
```

Validation:
- `endpoint` must be HTTPS
- `keys.p256dh` and `keys.auth` are required
- payload is stored in `users.push_subscription`

### Response 200

```json
{
  "subscribed": true,
  "updated_at": "2026-05-16T20:40:00Z"
}
```

---

## DELETE /api/v1/notifications/subscription

Remove the current user's push subscription.

### Response 200

```json
{
  "subscribed": false
}
```

---

## Push Payloads

Payloads are encrypted by the Web Push protocol. No receipt image URLs or sensitive notes are sent in push bodies.

### Field Worker Approval

Triggered after an approve or bulk approve transaction commits.

```json
{
  "type": "expense_decision",
  "expense_id": "expense-uuid",
  "status": "approved",
  "title": "Expense approved",
  "body": "EGP 1500.00 approved",
  "url": "/"
}
```

Arabic title/body are generated server-side from the user's preferred language when available. If language is unknown, Arabic is the default.

### Field Worker Rejection

Triggered after a reject transaction commits.

```json
{
  "type": "expense_decision",
  "expense_id": "expense-uuid",
  "status": "rejected",
  "title": "Expense rejected",
  "body": "EGP 1500.00 rejected: Receipt is unreadable",
  "url": "/"
}
```

### Accountant Batched Pending Notification

Triggered by Redis-backed batching after new pending expenses are created or resubmitted.

```json
{
  "type": "review_queue_batch",
  "count": 5,
  "title": "Expenses pending review",
  "body": "5 new expenses are waiting",
  "url": "/review"
}
```

Batching rules:
- Aggregate by `company_id`.
- Send to active users with role `accountant` or `admin` and non-null `push_subscription`.
- Debounce window: 5 minutes or threshold of 5 new pending expenses, whichever comes first.
- Do not send one notification per expense to accountants.

---

## Delivery Failure Handling

`pywebpush` delivery failures are handled as follows:

| Failure | Behavior |
|---------|----------|
| 404 or 410 from push service | Clear `users.push_subscription` for that user. |
| 400 invalid subscription | Clear subscription and log at warning level. |
| 429 or 5xx | Leave subscription intact; retry through normal batch loop/backoff. |
| Missing subscription | Skip silently. |
| VAPID not configured | Skip delivery in development/test and log configuration warning. |

Push failures must never roll back expense review transactions.

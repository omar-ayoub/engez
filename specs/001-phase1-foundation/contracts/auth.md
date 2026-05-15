# API Contract: Authentication

**Base path**: `/api/v1/auth`

## POST /login

Authenticate a user with email and password. Returns access + refresh tokens.

**Request**:
```json
{
  "email": "string (required)",
  "password": "string (required)"
}
```

**Response 200** (success):
```json
{
  "access_token": "string (JWT, 30min expiry)",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "string",
    "name": "string",
    "name_ar": "string",
    "role": "field_worker | accountant | admin",
    "company_id": "uuid",
    "company_name": "string",
    "company_name_ar": "string"
  }
}
```

**Response headers**: Sets `refresh_token` as httpOnly, secure, sameSite=strict cookie (7-day expiry).

**Response 401** (invalid credentials):
```json
{
  "detail": "البريد الإلكتروني أو كلمة المرور غير صحيحة",
  "detail_en": "Invalid email or password"
}
```

**Response 423** (account locked):
```json
{
  "detail": "تم تأمين الحساب. حاول مرة أخرى بعد 15 دقيقة",
  "detail_en": "Account locked. Try again in 15 minutes",
  "locked_until": "ISO 8601 timestamp"
}
```

**Response 403** (inactive account or company):
```json
{
  "detail": "الحساب غير نشط",
  "detail_en": "Account is inactive"
}
```

## POST /refresh

Silently refresh the access token using the refresh token cookie.

**Request**: No body. Refresh token read from httpOnly cookie.

**Response 200**:
```json
{
  "access_token": "string (new JWT, 30min expiry)",
  "token_type": "bearer"
}
```

**Response 401** (expired or invalid refresh token):
```json
{
  "detail": "انتهت صلاحية الجلسة. يرجى تسجيل الدخول مرة أخرى",
  "detail_en": "Session expired. Please log in again"
}
```

## POST /webauthn/register

Register a WebAuthn credential for biometric re-authentication. Requires valid access token.

**Request**:
```json
{
  "credential_id": "string (base64url)",
  "public_key": "string (base64url, CBOR-encoded)",
  "attestation": "string (base64url)"
}
```

**Response 200**:
```json
{
  "registered": true
}
```

## POST /webauthn/authenticate

Authenticate using a registered WebAuthn credential. Issues new token pair.

**Request**:
```json
{
  "credential_id": "string (base64url)",
  "authenticator_data": "string (base64url)",
  "client_data_json": "string (base64url)",
  "signature": "string (base64url)"
}
```

**Response 200**: Same as POST /login response.

**Response 401** (invalid credential):
```json
{
  "detail": "فشل التحقق البيومتري",
  "detail_en": "Biometric verification failed"
}
```

## POST /logout

Invalidate the refresh token cookie.

**Request**: No body.

**Response 200**:
```json
{
  "logged_out": true
}
```

**Response headers**: Clears `refresh_token` cookie.

## Common Headers

All authenticated endpoints require:
```
Authorization: Bearer <access_token>
```

All responses include:
```
Content-Type: application/json
```

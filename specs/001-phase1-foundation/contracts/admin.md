# API Contract: Admin Management

**Base path**: `/api/v1`

**Authorization**: All endpoints require `role: admin`. Non-admin users receive 403.

**Tenant scoping**: All list/get operations automatically filter by the admin's `company_id` from their JWT token. Admins can only manage their own company's data.

## Companies

### GET /companies/me

Get the current admin's company details.

**Response 200**:
```json
{
  "id": "uuid",
  "name": "string",
  "name_ar": "string",
  "tax_registration": "string | null",
  "is_active": true,
  "settings": {},
  "created_at": "ISO 8601",
  "updated_at": "ISO 8601"
}
```

### PATCH /companies/me

Update the current admin's company.

**Request** (partial update):
```json
{
  "name": "string (optional)",
  "name_ar": "string (optional)",
  "tax_registration": "string | null (optional)",
  "settings": "{} (optional)"
}
```

**Response 200**: Updated company object.

## Users

### GET /users

List users in the admin's company.

**Query params**: `?role=field_worker&is_active=true&page=1&per_page=20`

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "email": "string",
      "name": "string",
      "name_ar": "string",
      "role": "field_worker | accountant | admin",
      "is_active": true,
      "created_at": "ISO 8601"
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

### POST /users

Create a new user in the admin's company.

**Request**:
```json
{
  "email": "string (required, unique globally)",
  "name": "string (required)",
  "name_ar": "string (required)",
  "password": "string (required, min 8 chars)",
  "role": "field_worker | accountant | admin (required)"
}
```

**Response 201**: Created user object (without password).

**Response 409** (duplicate email):
```json
{
  "detail": "البريد الإلكتروني مسجل بالفعل",
  "detail_en": "Email already registered"
}
```

### PATCH /users/{user_id}

Update a user. Cannot change `company_id` or `email`.

**Request** (partial update):
```json
{
  "name": "string (optional)",
  "name_ar": "string (optional)",
  "role": "string (optional)",
  "is_active": "boolean (optional)",
  "password": "string (optional, min 8 chars)"
}
```

**Response 200**: Updated user object.

**Response 404**: User not found in admin's company.

## Projects

### GET /projects

List projects in the admin's company.

**Query params**: `?is_active=true&page=1&per_page=20`

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "string",
      "name_ar": "string",
      "code": "string",
      "budget": "number | null",
      "is_active": true,
      "created_at": "ISO 8601"
    }
  ],
  "total": 10,
  "page": 1,
  "per_page": 20
}
```

### POST /projects

Create a new project.

**Request**:
```json
{
  "name": "string (required)",
  "name_ar": "string (required)",
  "code": "string (required, unique within company)",
  "budget": "number | null (optional)"
}
```

**Response 201**: Created project object.

**Response 409** (duplicate code):
```json
{
  "detail": "كود المشروع مستخدم بالفعل",
  "detail_en": "Project code already exists"
}
```

### PATCH /projects/{project_id}

Update a project.

**Request** (partial update):
```json
{
  "name": "string (optional)",
  "name_ar": "string (optional)",
  "budget": "number | null (optional)",
  "is_active": "boolean (optional)"
}
```

**Response 200**: Updated project object.

## Categories

### GET /categories

List expense categories in the admin's company.

**Query params**: `?is_active=true`

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "string",
      "name_ar": "string",
      "sort_order": 0,
      "is_active": true
    }
  ]
}
```

### POST /categories

Create a new category.

**Request**:
```json
{
  "name": "string (required)",
  "name_ar": "string (required)",
  "sort_order": "integer (optional, default 0)"
}
```

**Response 201**: Created category object.

**Response 409** (duplicate name):
```json
{
  "detail": "اسم الفئة مستخدم بالفعل",
  "detail_en": "Category name already exists"
}
```

### PATCH /categories/{category_id}

Update a category.

**Request** (partial update):
```json
{
  "name": "string (optional)",
  "name_ar": "string (optional)",
  "sort_order": "integer (optional)",
  "is_active": "boolean (optional)"
}
```

**Response 200**: Updated category object.

## Common Error Responses

**401 Unauthorized**: Missing or invalid access token.
```json
{
  "detail": "غير مصرح",
  "detail_en": "Not authenticated"
}
```

**403 Forbidden**: User does not have admin role.
```json
{
  "detail": "غير مسموح",
  "detail_en": "Not authorized"
}
```

**422 Validation Error**: Invalid request body.
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "validation error message",
      "type": "error_type"
    }
  ]
}
```

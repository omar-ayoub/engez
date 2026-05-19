# Quickstart: Integration & Analytics

**Branch**: `004-integration-analytics`

## Prerequisites

- Backend running (`uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`)
- PostgreSQL 16 with migrations applied (`uv run alembic upgrade head`)
- Redis 7 running (for background task scheduling)
- Frontend dev server (`pnpm dev`)

## New Dependencies

### Backend
```bash
cd backend
uv add openpyxl    # Excel export generation
uv add cryptography  # AES-256-GCM credential encryption
# Pillow already installed (used for QR decode)
# httpx already installed (used for AI services)
```

### Frontend
```bash
cd frontend
pnpm add recharts    # Chart library for analytics dashboard
```

## Database Migration

After adding new models (`IntegrationConfig`, `ExportRecord`, `budget` on Project):

```bash
cd backend
uv run alembic revision --autogenerate -m "add integration and export tables"
uv run alembic upgrade head
```

## Environment Variables

Add to `.env`:
```bash
# Encryption master key for ERP credentials (generate with: python -c "import secrets; print(secrets.token_hex(32))")
CREDENTIAL_MASTER_KEY=<64-char-hex-string>
```

## Key Implementation Order

1. **Models + Migration** — IntegrationConfig, ExportRecord, budget field
2. **Crypto service** — AES-256-GCM encrypt/decrypt for credentials
3. **Exporter base + registry** — Abstract interface + adapter registration
4. **Anomaly detection service** — All 4 detection types
5. **API routers** — Integrations, anomalies, analytics endpoints
6. **Frontend analytics** — Recharts dashboard + export
7. **Frontend integrations** — Settings page + status views

## Running Tests

```bash
# Backend (existing test infrastructure)
cd backend
uv run pytest tests/test_integration_export.py -v
uv run pytest tests/test_anomaly_detection.py -v
uv run pytest tests/test_analytics.py -v

# E2E (Playwright)
cd frontend
pnpm test:e2e -- --grep "Analytics|Integration|Anomaly"
```

## Verification Checklist

- [ ] `POST /api/v1/integrations/test-connection` returns success with valid Zoho creds
- [ ] Approving an expense triggers background export within 60s
- [ ] Submitting a duplicate receipt image triggers anomaly flag within 30s
- [ ] `/analytics` page renders 4 charts with sample data
- [ ] CSV/Excel export downloads correctly
- [ ] All queries are scoped by company_id (no cross-tenant leaks)

# Implementation Plan: Integration & Analytics

**Branch**: `004-integration-analytics` | **Date**: 2026-05-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-integration-analytics/spec.md`

## Summary

Build the enterprise integration layer (ERP export with adapter pattern), AI anomaly detection system (duplicate receipts, statistical outliers, velocity checks, vendor/category mismatches), and spend analytics dashboard (charts + CSV/Excel export). All three modules are online-only features targeting accountant/admin/CFO users.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript 6.0 (frontend)

**Primary Dependencies**: FastAPI 0.136, SQLAlchemy 2.0 async, httpx (ERP API calls), Pillow (image hashing), openpyxl (Excel export), React 19.2, Recharts 2.x (charts), Zustand 5

**Storage**: PostgreSQL 16 (primary), Redis 7 (background task queuing)

**Testing**: pytest + pytest-asyncio (backend), Playwright 1.60 (E2E)

**Target Platform**: Web PWA — desktop-optimized views for accountant/CFO (online-only)

**Project Type**: Web application (frontend + backend)

**Performance Goals**: 3s chart render (10K expenses), 60s export push to ERP, 30s anomaly detection SLA, 10s CSV/Excel export

**Constraints**: Multi-tenant isolation (company_id), AES-256 credential encryption, advisory-only anomaly flags, live queries (no pre-aggregation)

**Scale/Scope**: Up to 10,000 approved expenses per company, 3 ERP adapters, 4 anomaly detection types, 4 chart types + export

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Offline-First | JUSTIFIED VIOLATION | Integration settings, analytics dashboard, and ERP sync are online-only. Field worker expense submission remains offline-first. Accountant/CFO users operate with reliable office internet (documented in spec assumptions). |
| II | Arabic-First RTL | PASS | Dashboard uses Arabic labels, RTL layout, LTR amounts. All strings externalized via i18n. |
| III | Multi-Tenant Isolation | PASS | All queries scoped by company_id. Integration configs isolated per company. Receipt hash comparisons scoped by company. |
| IV | Field-Worker UX | PASS | These features target accountant/CFO (not field workers). Anomaly detection is transparent to field workers (async, non-blocking). |
| V | Spec-Driven Development | PASS | Full spec-kit workflow executed (specify → clarify → plan). |
| VI | Security by Default | PASS | AES-256 credential encryption, signed URLs for receipts, rate limiting on external API calls, admin-only access. |

## Project Structure

### Documentation (this feature)

```text
specs/004-integration-analytics/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contracts)
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/v1/
│   │   ├── integrations.py      # ERP integration endpoints
│   │   ├── analytics.py         # Spend analytics endpoints
│   │   └── anomalies.py         # Anomaly detection endpoints + metrics
│   ├── models/
│   │   ├── integration.py       # IntegrationConfig, ExportRecord models
��   │   └── expense.py           # (existing — anomaly_flags JSONB already exists)
│   ├── schemas/
│   │   ├── integration.py       # Pydantic schemas for integrations
│   │   └── analytics.py         # Pydantic schemas for analytics
│   └── services/
│       ├── exporters/
│       │   ├── __init__.py      # Exporter registry
│       │   ├── base.py          # Abstract ExpenseExporter interface
│       │   ├── zoho_books.py    # Zoho Books adapter
│       ��   ├── odoo_xmlrpc.py   # Odoo XML-RPC adapter
│       │   └── csv_daftra.py    # CSV export for Daftra
│       ├── anomaly.py           # Anomaly detection service
│       ├── analytics.py         # Analytics query service
│       └── crypto.py            # AES-256 credential encryption
├── tests/
│   ├── test_integration_export.py   # (already created)
│   ├── test_anomaly_detection.py    # (already created)
│   └── test_analytics.py           # (already created)
└── alembic/versions/               # New migration for integration tables

frontend/
├── src/
│   └── features/
│       ├── analytics/
│       │   ├── components/
│       │   │   ├── SpendByProjectBar.tsx
│       │   │   ├── SpendByCategoryDonut.tsx
│       │   │   ├── SpendTrendLine.tsx
│       │   │   ├── BudgetVsActualBar.tsx
│       │   │   ├── DashboardSummary.tsx
│       │   │   └── ExportButton.tsx
│       │   ├── hooks/
│       │   │   └── useAnalytics.ts
│       │   ├── pages/
│       │   │   └── AnalyticsDashboard.tsx
│       │   └── api.ts
│       └── integrations/
│           ├── components/
│           │   ├── IntegrationCard.tsx
│           │   ├── ConfigForm.tsx
│           │   ├── ConnectionStatus.tsx
│           │   └── ExportStatusList.tsx
│           ├── pages/
│           │   ├── IntegrationSettings.tsx
│           │   └── AnomalyMetrics.tsx
│           └── api.ts
└── e2e/
    └── integration-analytics.spec.ts  # (already created)
```

**Structure Decision**: Web application with feature-based frontend modules (analytics, integrations). Backend follows existing pattern: routers in `api/v1/`, business logic in `services/`, models in `models/`. The exporter pattern uses a dedicated subdirectory for adapter extensibility.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Offline-First (Principle I) — Dashboard and ERP sync are online-only | These features inherently require network access (querying live server data, calling external APIs). Target users (accountant/CFO) operate in offices with reliable internet. | Caching dashboard data offline would add complexity without user value — the data must be real-time to be useful for financial decisions. |

# Tasks: Integration & Analytics

**Input**: Design documents from `specs/004-integration-analytics/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included (test files already created during specification phase)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/app/` (models, services, api, schemas)
- **Frontend**: `frontend/src/features/` (analytics, integrations)
- **Tests**: `backend/tests/`, `frontend/e2e/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install new dependencies and create project structure

- [x] T001 [P] Add backend dependencies (openpyxl, cryptography) in backend/pyproject.toml
- [x] T002 [P] Add frontend dependency (recharts) in frontend/package.json
- [x] T003 [P] Create frontend feature directories: frontend/src/features/analytics/ and frontend/src/features/integrations/
- [x] T004 [P] Create backend service directory: backend/app/services/exporters/
- [x] T005 [P] Add i18n namespace files: frontend/src/locales/ar/analytics.json and frontend/src/locales/en/analytics.json
- [x] T006 [P] Add i18n namespace files: frontend/src/locales/ar/integrations.json and frontend/src/locales/en/integrations.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Create IntegrationConfig model in backend/app/models/integration.py (fields: id, company_id, system_name, encrypted_credentials, oauth_refresh_token, status, last_sync_at, last_error, field_mappings, timestamps)
- [x] T008 Create ExportRecord model in backend/app/models/export_record.py (fields: id, company_id, expense_id, system_name, status, external_ref_id, error_message, attempt_count, next_retry_at, timestamps)
- [x] T009 Add budget column to Project model in backend/app/models/project.py (Numeric 14,2, nullable)
- [x] T010 Add receipt_hash index to Expense model: ix_expenses_company_receipt_hash on (company_id, receipt_hash) in backend/app/models/expense.py
- [x] T011 Generate Alembic migration for new tables and columns: backend/alembic/versions/xxx_add_integration_export_tables.py
- [x] T012 Create crypto service for AES-256-GCM credential encryption in backend/app/services/crypto.py (encrypt, decrypt, derive_company_key from master key via HKDF)
- [x] T013 Create abstract ExpenseExporter base class in backend/app/services/exporters/base.py (push, test_connection, get_required_config_fields methods)
- [x] T014 Create exporter registry in backend/app/services/exporters/__init__.py (EXPORTERS dict mapping system_name to class, get_exporter factory)
- [x] T015 Create integration Pydantic schemas in backend/app/schemas/integration.py (ConfigureRequest, IntegrationStatus, ExportRecordResponse, TestConnectionResponse)
- [x] T016 Create analytics Pydantic schemas in backend/app/schemas/analytics.py (SpendByProject, SpendByCategory, SpendTrend, BudgetVsActual, Summary, ExportParams)
- [x] T017 Register new models in backend/app/models/__init__.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - ERP Export (Priority: P1) MVP

**Goal**: Approved expenses automatically push to configured accounting system within 60 seconds

**Independent Test**: Approve an expense → verify ExportRecord created with status "success" and external_ref_id populated (mock external API in tests)

### Implementation for User Story 1

- [x] T018 [P] [US1] Implement Zoho Books adapter in backend/app/services/exporters/zoho_books.py (push expense as entry, test_connection, OAuth2 refresh on 401)
- [x] T019 [P] [US1] Implement Odoo XML-RPC adapter in backend/app/services/exporters/odoo_xmlrpc.py (push expense as journal entry, test_connection)
- [x] T020 [P] [US1] Implement CSV Daftra adapter in backend/app/services/exporters/csv_daftra.py (generate CSV with Arabic headers for date range)
- [x] T021 [US1] Create export orchestration service in backend/app/services/export_orchestrator.py (trigger export on approval, create ExportRecord, handle retry with exponential backoff, idempotency check)
- [x] T022 [US1] Create integrations API router in backend/app/api/v1/integrations.py (GET /available, POST /configure, POST /test-connection, GET /status, POST /export/{id}, POST /export/{id}/retry, GET /exports, GET /csv-export)
- [x] T023 [US1] Register integrations router in backend/app/api/v1/__init__.py
- [x] T024 [US1] Wire export trigger into expense approval flow: update backend/app/services/review_actions.py to call export_orchestrator after successful approve
- [x] T025 [US1] Implement retry background task: check failed exports where next_retry_at <= now(), re-attempt, update attempt_count and next_retry_at with exponential backoff
- [x] T026 [US1] Implement integration switching logic: on reconfigure, cancel pending exports (status: cancelled_migration) for old system
- [x] T027 [US1] Add credential expiry notification: when adapter returns auth error, update IntegrationConfig status to "needs_reauth" and trigger admin notification via push_notifications service

**Checkpoint**: User Story 1 fully functional — approving an expense triggers export to configured ERP

---

## Phase 4: User Story 2 - Anomaly Detection (Priority: P1)

**Goal**: Advisory anomaly flags appear on expenses within 30 seconds of submission (async, never blocking)

**Independent Test**: Submit an expense with a duplicate receipt hash → verify anomaly_flags JSONB populated with duplicate_receipt flag within 30 seconds

### Implementation for User Story 2

- [x] T028 [US2] Create anomaly detection service in backend/app/services/anomaly.py (detect_anomalies orchestrator, compute_perceptual_hash, check_duplicate_receipt, check_statistical_outlier, check_submission_velocity, check_vendor_category_mismatch)
- [x] T029 [US2] Create anomalies API router in backend/app/api/v1/anomalies.py (POST /expenses/check-anomalies, GET /anomalies/metrics)
- [x] T030 [US2] Register anomalies router in backend/app/api/v1/__init__.py
- [x] T031 [US2] Wire anomaly detection as BackgroundTask after expense creation: update backend/app/api/v1/expenses.py to trigger detect_anomalies after successful expense save
- [x] T032 [US2] Implement duplicate receipt detection: query ix_expenses_company_receipt_hash index, compute Hamming distance, flag if similarity > 90%
- [x] T033 [US2] Implement statistical outlier detection: query AVG/STDDEV for user+category with minimum 5 historical expenses threshold, flag if amount > mean + 2*std
- [x] T034 [US2] Implement velocity check: count expenses by user in last 10 minutes, flag if >= 3
- [x] T035 [US2] Implement vendor/category mismatch: query historical category distribution for vendor, flag if assigned category differs from 80%+ historical pattern
- [x] T036 [US2] Update review queue service to include anomaly_flags in queue response (badge counts) in backend/app/services/review_queue.py
- [x] T037 [US2] Add anomaly badges to review detail view: update frontend/src/features/review/components/ to display severity-colored badges from anomaly_flags

**Checkpoint**: User Story 2 fully functional — submitted expenses get async anomaly flags visible in review queue

---

## Phase 5: User Story 3 - Analytics Dashboard (Priority: P2)

**Goal**: CFO views live spend visualizations (4 chart types) with project/period filtering

**Independent Test**: Navigate to /analytics → verify all 4 charts render with data and period filter updates the view

### Implementation for User Story 3

- [x] T038 [US3] Create analytics query service in backend/app/services/analytics.py (spend_by_project, spend_by_category, spend_trend, budget_vs_actual, summary — all scoped by company_id, approved status only)
- [x] T039 [US3] Create analytics API router in backend/app/api/v1/analytics.py (GET /spend-by-project, GET /spend-by-category, GET /spend-trend, GET /budget-vs-actual, GET /summary, GET /export)
- [x] T040 [US3] Register analytics router in backend/app/api/v1/__init__.py
- [x] T041 [US3] Create analytics API client in frontend/src/features/analytics/api.ts (fetchSpendByProject, fetchSpendByCategory, fetchSpendTrend, fetchBudgetVsActual, fetchSummary)
- [x] T042 [US3] Create useAnalytics hook in frontend/src/features/analytics/hooks/useAnalytics.ts (manage period state, fetch all endpoints, loading/error states)
- [x] T043 [P] [US3] Create DashboardSummary component in frontend/src/features/analytics/components/DashboardSummary.tsx (KPI cards: total spend, expense count, project count)
- [x] T044 [P] [US3] Create SpendByProjectBar chart in frontend/src/features/analytics/components/SpendByProjectBar.tsx (horizontal bar chart with Arabic labels, budget line overlay)
- [x] T045 [P] [US3] Create SpendByCategoryDonut chart in frontend/src/features/analytics/components/SpendByCategoryDonut.tsx (donut chart with category names)
- [x] T046 [P] [US3] Create SpendTrendLine chart in frontend/src/features/analytics/components/SpendTrendLine.tsx (weekly line chart with area fill)
- [x] T047 [P] [US3] Create BudgetVsActualBar chart in frontend/src/features/analytics/components/BudgetVsActualBar.tsx (grouped bar comparing budget vs actual)
- [x] T048 [US3] Create AnalyticsDashboard page in frontend/src/features/analytics/pages/AnalyticsDashboard.tsx (compose all charts + period filter + summary KPIs)
- [x] T049 [US3] Add /analytics route to frontend/src/App.tsx (protected, role: accountant or admin)

**Checkpoint**: User Story 3 fully functional — /analytics page renders live charts for the authenticated company

---

## Phase 6: User Story 4 - Analytics Export (Priority: P2)

**Goal**: Export any analytics view to CSV or Excel format reflecting current filters

**Independent Test**: Apply a 90-day filter → click Export CSV → verify downloaded file contains correct columns and filtered data

### Implementation for User Story 4

- [x] T050 [US4] Implement CSV export in backend analytics router: generate CSV response with Arabic column headers using csv module in backend/app/api/v1/analytics.py
- [x] T051 [US4] Implement Excel export in backend analytics router: generate .xlsx response using openpyxl with formatted headers in backend/app/api/v1/analytics.py
- [x] T052 [US4] Create ExportButton component in frontend/src/features/analytics/components/ExportButton.tsx (dropdown: CSV, Excel; triggers download for current view + filters)
- [x] T053 [US4] Integrate ExportButton into AnalyticsDashboard page in frontend/src/features/analytics/pages/AnalyticsDashboard.tsx

**Checkpoint**: User Story 4 fully functional — CSV and Excel exports download with correct filtered data

---

## Phase 7: User Story 5 - Integration Configuration UI (Priority: P3)

**Goal**: Admin configures ERP integration, tests connection, and sees current status

**Independent Test**: Navigate to /settings/integrations → select Zoho → enter credentials → click Test Connection → verify success/error feedback

### Implementation for User Story 5

- [x] T054 [P] [US5] Create integration API client in frontend/src/features/integrations/api.ts (getAvailable, configure, testConnection, getStatus, getExports)
- [x] T055 [P] [US5] Create IntegrationCard component in frontend/src/features/integrations/components/IntegrationCard.tsx (display system name, status badge, last sync time)
- [x] T056 [P] [US5] Create ConfigForm component in frontend/src/features/integrations/components/ConfigForm.tsx (dynamic fields based on system_name, test connection button, save)
- [x] T057 [P] [US5] Create ConnectionStatus component in frontend/src/features/integrations/components/ConnectionStatus.tsx (active/error/needs_reauth badge with last error)
- [x] T058 [P] [US5] Create ExportStatusList component in frontend/src/features/integrations/components/ExportStatusList.tsx (list exports with status, retry button for failed)
- [x] T059 [US5] Create IntegrationSettings page in frontend/src/features/integrations/pages/IntegrationSettings.tsx (compose cards, config form, status, export list)
- [x] T060 [US5] Add /settings/integrations route to frontend/src/App.tsx (protected, role: admin or accountant)

**Checkpoint**: User Story 5 fully functional — admin can configure, test, and monitor ERP integration

---

## Phase 8: User Story 6 - Anomaly Metrics (Priority: P3)

**Goal**: Admin views anomaly detection performance metrics (flags by type, rejection correlation)

**Independent Test**: Navigate to /settings/anomaly-metrics → verify total flags count and breakdown by type displayed

### Implementation for User Story 6

- [x] T061 [US6] Implement metrics aggregation logic in anomaly service: count flags by type from expense.anomaly_flags JSONB, compute rejection correlation in backend/app/services/anomaly.py
- [x] T062 [US6] Create AnomalyMetrics page in frontend/src/features/integrations/pages/AnomalyMetrics.tsx (total flags, by-type breakdown, rejection correlation indicator)
- [x] T063 [US6] Add /settings/anomaly-metrics route to frontend/src/App.tsx (protected, role: admin)

**Checkpoint**: User Story 6 fully functional — admin can monitor anomaly detection system health

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T064 [P] Add RTL-compatible chart styling (LTR numbers, Arabic labels) across all Recharts components in frontend/src/features/analytics/components/
- [x] T065 [P] Add dark mode theming for charts (respect system dark mode default) in frontend/src/features/analytics/components/
- [x] T066 [P] Add loading skeletons for dashboard charts in frontend/src/features/analytics/components/
- [x] T067 [P] Add empty state for analytics when no approved expenses exist in frontend/src/features/analytics/pages/AnalyticsDashboard.tsx
- [x] T068 Ensure all analytics and integration queries enforce company_id tenant scope — add integration test for tenant isolation
- [x] T069 Add navigation links to analytics and integration settings in app sidebar/nav
- [ ] T070 Run E2E tests: pnpm test:e2e -- --grep "Analytics|Integration|Anomaly" and fix any failures
- [ ] T071 Run backend tests: uv run pytest tests/test_integration_export.py tests/test_anomaly_detection.py tests/test_analytics.py and fix any failures
- [ ] T072 Validate quickstart.md checklist items pass end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - US1 and US2 can proceed in parallel (P1 priority, independent modules)
  - US3 and US4 can proceed in parallel with US1/US2 (different concerns)
  - US5 depends on US1 backend (integration router) being complete
  - US6 depends on US2 backend (anomaly service) being complete
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (ERP Export)**: Foundational only — independent
- **US2 (Anomaly Detection)**: Foundational only — independent
- **US3 (Analytics Dashboard)**: Foundational only — independent
- **US4 (Analytics Export)**: Depends on US3 (adds export to existing dashboard)
- **US5 (Integration Config UI)**: Depends on US1 backend (router must exist for frontend to call)
- **US6 (Anomaly Metrics)**: Depends on US2 backend (metrics endpoint must exist)

### Within Each User Story

- Models before services (already in Foundational)
- Services before API endpoints
- API endpoints before frontend components
- Core implementation before integration with other stories

### Parallel Opportunities

- **Phase 1**: All 6 tasks can run in parallel (different files)
- **Phase 2**: T007-T010 (models) in parallel, then T011 (migration), then T012-T017 in parallel
- **Phase 3**: T018-T020 (adapters) in parallel, then T021+ sequentially
- **Phase 4**: T032-T035 (detection algorithms) could be parallel within anomaly.py but share the file
- **Phase 5**: T043-T047 (chart components) all in parallel (different files)
- **Phase 7**: T054-T058 (integration UI components) all in parallel

---

## Parallel Example: User Story 3 (Analytics Dashboard)

```bash
# Launch all chart components in parallel (different files):
Task: "Create SpendByProjectBar in frontend/src/features/analytics/components/SpendByProjectBar.tsx"
Task: "Create SpendByCategoryDonut in frontend/src/features/analytics/components/SpendByCategoryDonut.tsx"
Task: "Create SpendTrendLine in frontend/src/features/analytics/components/SpendTrendLine.tsx"
Task: "Create BudgetVsActualBar in frontend/src/features/analytics/components/BudgetVsActualBar.tsx"
Task: "Create DashboardSummary in frontend/src/features/analytics/components/DashboardSummary.tsx"

# Then compose into page (depends on all above):
Task: "Create AnalyticsDashboard page composing all charts"
```

---

## Parallel Example: User Story 1 (ERP Export)

```bash
# Launch all adapters in parallel (different files):
Task: "Implement Zoho Books adapter in backend/app/services/exporters/zoho_books.py"
Task: "Implement Odoo XML-RPC adapter in backend/app/services/exporters/odoo_xmlrpc.py"
Task: "Implement CSV Daftra adapter in backend/app/services/exporters/csv_daftra.py"

# Then orchestrator (depends on adapters + registry):
Task: "Create export orchestration service"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup (install deps, create directories)
2. Complete Phase 2: Foundational (models, migration, crypto, base exporter)
3. Complete Phase 3: US1 — ERP Export
4. Complete Phase 4: US2 — Anomaly Detection
5. **STOP and VALIDATE**: Test both stories independently
6. Deploy/demo: Expenses export to ERP + anomaly flags on review queue

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (ERP Export) → Test independently → Core value delivered
3. US2 (Anomaly Detection) → Test independently → Financial controls active
4. US3 (Analytics Dashboard) → Test independently → CFO visibility
5. US4 (Analytics Export) → Test independently → Data portability
6. US5 (Integration Config UI) → Test independently → Self-service setup
7. US6 (Anomaly Metrics) → Test independently → Operational visibility
8. Polish → Production-ready

### Solo Developer Strategy (Recommended)

Since this is a solo project, execute sequentially in priority order:

1. Phase 1 + Phase 2 (Setup + Foundational): ~2 hours
2. Phase 3 (US1 ERP Export): ~4 hours
3. Phase 4 (US2 Anomaly Detection): ~3 hours
4. Phase 5 (US3 Analytics Dashboard): ~4 hours
5. Phase 6 (US4 Analytics Export): ~1 hour
6. Phase 7 (US5 Integration Config UI): ~3 hours
7. Phase 8 (US6 Anomaly Metrics): ~1 hour
8. Phase 9 (Polish): ~2 hours

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Test files already created (test_integration_export.py, test_anomaly_detection.py, test_analytics.py, integration-analytics.spec.ts)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All external API calls (Zoho, Odoo) MUST be mocked in tests — no live API calls during testing

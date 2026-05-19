# Feature Specification: Integration & Analytics

**Feature Branch**: `004-integration-analytics`

**Created**: 2026-05-17

**Status**: Clarified

**Input**: User description: "Build the enterprise integration layer and analytics dashboard that justify the CFO's subscription. Accounting system integration via an abstraction layer (ExpenseExporter interface). First adapters: Zoho Books API, Odoo XML-RPC, and CSV export for Daftra. AI anomaly detection system with duplicate receipt detection, statistical outlier detection, velocity checks, and vendor/category mismatch detection. Spend analytics dashboard for the CFO."

## Clarifications

### Session 2026-05-17

- Q: How should ERP credentials be stored and what happens on token expiry? → A: OAuth2 refresh token flow where supported (Zoho); AES-256 encrypted at rest; admin manually re-authenticates on expiry (notification-driven)
- Q: Should anomaly flags be stored as a separate database table or within the existing Expense record? → A: Stored in the existing anomaly_flags JSONB column on the Expense model (no separate table)
- Q: When a company switches integrations, what happens to pending/failed exports? → A: Pending/failed exports are cancelled (status: cancelled_migration); successful export references retained permanently
- Q: Should anomaly detection run synchronously during submission or asynchronously? → A: Asynchronous background task; flags appear within 30 seconds of expense submission
- Q: Should analytics use live queries or pre-aggregated snapshots? → A: Live queries against approved expenses; no pre-aggregation needed at current scale (up to 10,000 expenses)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Accountant Exports Approved Expenses to Accounting System (Priority: P1)

The accountant configures one of the supported accounting systems (Zoho Books, Odoo, or CSV/Daftra) for their company. When expenses are approved, the system automatically pushes them to the configured external accounting system as journal entries. The accountant can see the export status of each expense and retry failed exports.

**Why this priority**: Without ERP integration, accountants must manually re-enter approved expenses into their accounting software — the #1 reason companies abandon expense tools.

**Independent Test**: Can be fully tested by approving an expense and verifying it appears as a journal entry in the connected system (or exported file). Delivers immediate time savings.

**Acceptance Scenarios**:

1. **Given** a company has configured Zoho Books credentials, **When** an expense is approved, **Then** the system pushes it as an expense entry to Zoho Books within 60 seconds and records the external reference ID.
2. **Given** a company has configured Odoo credentials, **When** an expense is approved, **Then** the system pushes it as a journal entry via XML-RPC within 60 seconds.
3. **Given** a company has selected CSV export for Daftra, **When** the accountant requests an export, **Then** the system generates a downloadable CSV file containing all approved expenses for the selected date range.
4. **Given** an export to an external system fails (network error, auth expired), **When** the accountant views export status, **Then** the failed expense shows "export failed" with error details and a retry button.
5. **Given** a company has no integration configured, **When** the accountant navigates to integration settings, **Then** they see available integration options with setup instructions.

---

### User Story 2 - Anomaly Detection Flags Suspicious Expenses (Priority: P1)

When a field worker submits an expense, the system triggers an asynchronous anomaly detection task. Flagged anomalies appear as advisory badges on the review queue within 30 seconds — they never block submission or auto-reject. The accountant sees these flags while reviewing and can make informed decisions.

**Why this priority**: Fraud prevention and financial controls are the primary value proposition that justifies the CFO's subscription over simpler tools.

**Independent Test**: Can be tested by submitting expenses that trigger each anomaly type and verifying flags appear on the review queue with correct severity within 30 seconds.

**Acceptance Scenarios**:

1. **Given** a receipt image that is >90% similar to a previously submitted receipt (same company), **When** the expense is submitted, **Then** the system flags it with "duplicate receipt" (high severity) and links to the similar expense within 30 seconds.
2. **Given** a user submits an expense with amount >2 standard deviations above their mean for that category, **When** the expense is processed, **Then** it is flagged with "statistical outlier" (medium severity) showing the average and deviation.
3. **Given** a user submits 3 or more expenses within 10 minutes, **When** the third expense arrives, **Then** all recent expenses are flagged with "high velocity" (medium severity).
4. **Given** a vendor that is typically associated with category X, **When** an expense assigns it to category Y, **Then** the expense is flagged with "vendor/category mismatch" (low severity).
5. **Given** an expense has anomaly flags, **When** the accountant approves it anyway, **Then** the approval proceeds normally (flags are advisory only).

---

### User Story 3 - CFO Views Spend Analytics Dashboard (Priority: P2)

The CFO (or any admin/accountant) accesses a spend analytics dashboard showing live visualizations of company spending patterns queried directly from approved expense data. They can filter by time period, project, and team. The dashboard helps identify budget overruns, spending trends, and team-level patterns.

**Why this priority**: Executive visibility into spend data justifies the subscription fee and enables proactive budget management.

**Independent Test**: Can be tested by verifying that charts render correctly with sample data and that filters update the visualizations.

**Acceptance Scenarios**:

1. **Given** approved expenses exist for multiple projects, **When** the CFO views the dashboard, **Then** a bar chart shows spend by project for the selected period (30 or 90 days).
2. **Given** approved expenses exist across categories, **When** the CFO views the category breakdown, **Then** a donut chart shows proportional spend by category.
3. **Given** approved expenses span multiple weeks, **When** the CFO views the trend chart, **Then** a line chart shows weekly spend trend per team.
4. **Given** projects have defined budgets, **When** the CFO views budget comparison, **Then** a chart shows budget vs actual spend per active project with clear over/under indication.

---

### User Story 4 - CFO Exports Analytics Data (Priority: P2)

The CFO can export any analytics view to CSV or Excel format for use in board reports, external analysis, or compliance documentation.

**Why this priority**: Data portability is expected by enterprise customers and enables use cases beyond the dashboard.

**Independent Test**: Can be tested by triggering an export and verifying the downloaded file contains correct data matching the current filter state.

**Acceptance Scenarios**:

1. **Given** the CFO is viewing spend by project data, **When** they click export to CSV, **Then** a CSV file downloads with columns matching the chart data.
2. **Given** the CFO is viewing spend by project data, **When** they click export to Excel, **Then** an Excel file downloads with formatted data and column headers.
3. **Given** the CFO has applied filters (date range, project), **When** they export, **Then** the exported data reflects only the filtered view.

---

### User Story 5 - Admin Configures ERP Integration (Priority: P3)

An admin or accountant navigates to integration settings, selects an accounting system, enters the required credentials, and tests the connection. Once verified, the integration becomes active for their company. Credentials are stored AES-256 encrypted. For systems supporting OAuth2 (Zoho), the refresh token flow handles token renewal automatically until the refresh token itself expires, at which point the admin is notified to re-authenticate.

**Why this priority**: One-time setup flow; less frequently used than ongoing export and analytics.

**Independent Test**: Can be tested by configuring credentials and running a connection test that returns success or a clear error message.

**Acceptance Scenarios**:

1. **Given** an admin navigates to integration settings, **When** they select Zoho Books, **Then** they see required fields (access token, organization ID, expense account ID) with clear labels.
2. **Given** an admin enters valid credentials, **When** they click "Test Connection", **Then** the system confirms the connection is working within 5 seconds.
3. **Given** an admin enters invalid credentials, **When** they click "Test Connection", **Then** the system shows a clear error explaining what went wrong.
4. **Given** an integration is configured, **When** the admin views the settings page, **Then** they see the current status (active/error) and last successful sync timestamp.
5. **Given** a company has an active integration and the admin switches to a different system, **When** the switch is confirmed, **Then** pending/failed exports for the old system are cancelled and the new integration becomes active.

---

### User Story 6 - Admin Views AI Detection Metrics (Priority: P3)

An admin views metrics showing how the anomaly detection system is performing: total flags raised, flags per type, flag-to-rejection correlation, and false positive indicators.

**Why this priority**: Operational visibility helps tune the system over time but is not needed for initial launch.

**Independent Test**: Can be tested by verifying metrics endpoint returns correct counts aggregated from actual anomaly flag data.

**Acceptance Scenarios**:

1. **Given** anomaly flags have been generated over the past 30 days, **When** an admin views detection metrics, **Then** they see total flags, breakdown by type, and average flags per expense.
2. **Given** flagged expenses have been reviewed (some approved, some rejected), **When** an admin views metrics, **Then** they see the correlation between flags and rejection rate (precision indicator).

---

### Edge Cases

- What happens when the external accounting system is unreachable during export? → Export is queued and retried with exponential backoff (max 5 retries over 24 hours). Failed exports show in a "pending exports" list.
- What happens when ERP credentials expire mid-export? → The system marks the integration as "needs re-authentication", stops further exports, and notifies the admin via in-app notification.
- What happens when a duplicate receipt is detected but the original was rejected? → The flag still appears (advisory only) with context that the similar expense was previously rejected.
- What happens when there is insufficient historical data for statistical outlier detection? → The system requires a minimum of 5 expenses in the same user+category combination before flagging outliers. Below this threshold, no flag is raised.
- What happens when the perceptual hash computation fails (corrupted image)? → The duplicate check is skipped gracefully; other anomaly checks still run. A warning is logged.
- What happens when the CFO applies filters that return zero results? → The dashboard shows an empty state with a message indicating no data matches the filters and suggesting to adjust the date range.
- What happens when two exports to the same ERP overlap for the same expense? → Idempotency is enforced via the expense ID as external reference; duplicate pushes are detected and skipped.
- What happens when a project has no budget defined? → Budget vs actual chart omits that project or shows "No budget set" indicator.
- What happens when a company switches integrations while exports are pending? → Pending/failed exports for the old system are marked as "cancelled_migration". Successfully completed export references are retained permanently for audit purposes.

## Requirements *(mandatory)*

### Functional Requirements

#### Accounting System Integration

- **FR-001**: System MUST provide an abstraction layer for accounting system integrations where adding a new system requires only implementing a defined interface.
- **FR-002**: System MUST support Zoho Books integration, pushing approved expenses as expense entries with amount, date, currency, description, and project mapping.
- **FR-003**: System MUST support Odoo integration, pushing approved expenses as journal entries via the XML-RPC protocol.
- **FR-004**: System MUST support CSV export formatted for Daftra import, containing all standard expense fields with Arabic column headers.
- **FR-005**: System MUST automatically push approved expenses to the configured external system within 60 seconds of approval.
- **FR-006**: System MUST record the external reference ID returned by the accounting system for each successfully exported expense.
- **FR-007**: System MUST retry failed exports with exponential backoff (max 5 retries over 24 hours).
- **FR-008**: System MUST provide a "Test Connection" function that verifies credentials are valid before activating an integration.
- **FR-009**: System MUST display export status per expense (pending, success, failed) with error details for failures.
- **FR-010**: System MUST allow manual retry of failed exports.
- **FR-011**: System MUST enforce idempotency — re-exporting the same expense must not create duplicates in the external system.
- **FR-012**: System MUST notify the admin when integration credentials expire or become invalid.
- **FR-013**: Each company MUST be able to configure exactly one active accounting integration at a time.
- **FR-034**: System MUST store integration credentials encrypted at rest using AES-256 with company-level key isolation.
- **FR-035**: System MUST support OAuth2 refresh token flow for Zoho Books, automatically renewing access tokens until the refresh token expires.
- **FR-036**: When a company switches integrations, the system MUST cancel all pending/failed exports for the previous system (status: cancelled_migration) and retain successful export references permanently.

#### AI Anomaly Detection

- **FR-014**: System MUST detect duplicate receipts by comparing perceptual image hashes, flagging expenses with >90% similarity to a previously submitted receipt within the same company.
- **FR-015**: System MUST detect statistical outliers by flagging expenses with amounts exceeding 2 standard deviations above the user+category mean.
- **FR-016**: System MUST detect high submission velocity by flagging when a user submits 3 or more expenses within a 10-minute window.
- **FR-017**: System MUST detect vendor/category mismatches by flagging when a vendor is assigned to a category different from its historical pattern (based on 80%+ of prior assignments).
- **FR-018**: All anomaly flags MUST be advisory only — they MUST NOT block expense submission or auto-reject expenses.
- **FR-019**: Each anomaly flag MUST include a severity level (high, medium, low) and a human-readable message in Arabic and English.
- **FR-020**: Anomaly flags MUST appear as visual badges on the review queue and expense detail view.
- **FR-021**: System MUST require a minimum of 5 historical expenses in the same user+category combination before applying statistical outlier detection.
- **FR-022**: System MUST skip duplicate receipt detection gracefully when image hash computation fails, without blocking other checks.
- **FR-023**: System MUST provide an admin-accessible metrics view showing total flags, breakdown by type, and flag-to-rejection correlation.
- **FR-037**: Anomaly detection MUST run asynchronously as a background task triggered after expense submission completes, with flags appearing within 30 seconds.
- **FR-038**: Anomaly flags MUST be stored in the existing anomaly_flags JSONB field on the expense record (no separate entity table).

#### Spend Analytics Dashboard

- **FR-024**: System MUST provide a "Spend by Project" bar chart showing total approved spend per project for a configurable period (30 or 90 days).
- **FR-025**: System MUST provide a "Spend by Category" donut chart showing proportional spend distribution across categories.
- **FR-026**: System MUST provide a "Spend Trend" line chart showing weekly aggregated spend per team over a configurable period (up to 365 days).
- **FR-027**: System MUST provide a "Budget vs Actual" chart comparing defined project budgets against actual approved spend.
- **FR-028**: Dashboard MUST be accessible to users with accountant or admin roles only.
- **FR-029**: System MUST support export of any analytics view to CSV format.
- **FR-030**: System MUST support export of any analytics view to Excel format.
- **FR-031**: Exported data MUST reflect the currently applied filters (date range, project, team).
- **FR-032**: Dashboard MUST display data in the user's selected language (Arabic/English) with appropriate number formatting.
- **FR-033**: Dashboard charts MUST render within 3 seconds for companies with up to 10,000 approved expenses.
- **FR-039**: Analytics MUST query live approved expense data directly (no pre-aggregated materialized views) at the current target scale of up to 10,000 expenses per company.

### Key Entities

- **Integration Configuration**: Company-level record storing the selected accounting system type, AES-256 encrypted credentials (with company-level key isolation), OAuth2 refresh token (where supported), connection status, last successful sync timestamp, and required field mappings (e.g., project-to-account mapping).
- **Export Record**: Tracks each expense export attempt — expense ID, external system, status (pending/success/failed/cancelled_migration), external reference ID, error message, attempt count, last attempt timestamp. Successful export references are retained permanently even after integration switch.
- **Anomaly Flag** (stored as JSONB within Expense.anomaly_flags): Flag type (duplicate_receipt, statistical_outlier, high_velocity, vendor_mismatch), severity (high/medium/low), human-readable message (ar/en), metadata (e.g., similar_expense_id, average, std_dev). Populated asynchronously within 30 seconds of submission.
- **Receipt Hash**: Perceptual hash stored in the existing `receipt_hash` field on the Expense model for future duplicate comparisons within the same company.
- **Analytics Data**: Live queries against approved expenses — no separate snapshot entity. Queryable by project, category, team, and time period.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Approved expenses are exported to the configured accounting system within 60 seconds of approval, with a success rate of 95%+ (excluding credential failures).
- **SC-002**: Adding a new accounting system adapter requires implementing only the defined interface — no modifications to core export logic.
- **SC-003**: Duplicate receipt detection identifies >90% of re-submitted identical receipts within the same company.
- **SC-004**: Statistical outlier detection flags amounts exceeding 2 standard deviations with zero false positives on amounts within 1 standard deviation.
- **SC-005**: Velocity checks correctly flag all instances of 3+ expenses submitted within 10 minutes by the same user.
- **SC-006**: All anomaly flags are advisory — zero expenses are auto-rejected or blocked from submission due to flags.
- **SC-007**: Dashboard charts render within 3 seconds for datasets up to 10,000 approved expenses.
- **SC-008**: CSV and Excel exports complete within 10 seconds for datasets up to 10,000 records.
- **SC-009**: Integration setup (credential entry + connection test) can be completed by an admin in under 5 minutes.
- **SC-010**: Dashboard data accuracy: exported totals match the sum of individually approved expenses within the same filter criteria (zero drift).
- **SC-011**: Anomaly flags appear on submitted expenses within 30 seconds of submission (asynchronous processing target).

## Assumptions

- Companies operate with reliable internet at the accountant/admin level (ERP sync and dashboard are online-only features).
- Each company uses at most one accounting system integration at a time.
- Perceptual hashing uses average hash (aHash) algorithm — sufficient for detecting re-submissions of the same receipt photo.
- The minimum data threshold for statistical outlier detection (5 expenses per user+category) avoids false positives during early company onboarding.
- Vendor/category mismatch detection requires 80%+ historical consistency before flagging (prevents noise during early use).
- Project budgets are defined by admins in a separate settings area (already exists or assumed from previous features).
- Analytics queries run against approved expenses only — pending and rejected expenses are excluded. Live queries are used (no pre-aggregation) as the target scale of 10,000 expenses per company is well within direct query performance limits.
- Export credentials are stored AES-256 encrypted at rest with company-level key isolation. OAuth2 refresh tokens are used for Zoho Books; static API keys for Odoo.
- CSV export for Daftra uses their documented import format with Arabic column headers.
- Dashboard access is restricted to accountant and admin roles (field workers see only their own expense history).
- Anomaly detection runs asynchronously after expense submission to avoid blocking field worker UX. The 30-second SLA is sufficient since expenses are not reviewed immediately.

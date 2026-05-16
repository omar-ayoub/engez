# Feature Specification: Phase 1 — Foundation

**Feature Branch**: `001-phase1-foundation`

**Created**: 2026-05-15

**Status**: Draft

**Input**: User description: "Build the foundation layer of ENGEZ, a field expense capture Progressive Web App targeting Egyptian enterprises in construction, event management, and freight logistics. Phase 1 delivers: Arabic-first RTL design system, project scaffolding with offline-first architecture, JWT-based multi-tenant authentication with three roles, and a database schema supporting expenses, projects, users, companies, and AI correction feedback."

## Clarifications

### Session 2026-05-15

- Q: How is the first admin and company created when the system is brand new (bootstrap problem)? → A: A CLI seed command creates the initial company and admin user during deployment. No public registration page exists.
- Q: How are expense categories determined — free-text, predefined, or AI? → A: Admin defines a predefined category list per company. AI auto-suggests from that list based on receipt/voice data. Field workers select from the predefined list (no free-text).
- Q: Should login enforce brute-force protection? → A: Yes. Account locks after 5 consecutive failed attempts, auto-unlocks after 15 minutes.
- Q: What happens when the 24h session token expires? → A: Silent token refresh while user is active. On offline expiry + reconnect, prompt biometric authentication (fingerprint/face) for re-login instead of email/password. Falls back to email/password if biometrics unavailable.

## User Scenarios & Testing

### User Story 1 - Field Worker Logs In and Sees Home Screen (Priority: P1)

A field worker on a construction site opens the ENGEZ app on their phone. They enter their email and password on a simple login screen. The system authenticates them and lands them on a home screen that shows their company name, their role, and a clear path to submit an expense. The entire interface is in Arabic with right-to-left layout. The screen is dark-themed for outdoor readability.

**Why this priority**: Without authentication and a working home screen, no other feature can function. This is the entry point for every user journey in the application.

**Independent Test**: Can be fully tested by logging in with valid credentials and confirming the home screen renders in Arabic RTL with dark mode. Delivers the core "I can access the app" value.

**Acceptance Scenarios**:

1. **Given** a registered field worker with valid credentials, **When** they enter their email and password and tap "تسجيل الدخول" (Login), **Then** they are authenticated and redirected to the home screen showing their name and company in Arabic.
2. **Given** a user entering incorrect credentials, **When** they tap login, **Then** a calm, non-alarming error message appears in Arabic explaining the credentials are invalid.
3. **Given** a previously authenticated field worker, **When** they reopen the app within the session validity period, **Then** they bypass login and land directly on the home screen (persistent session).
4. **Given** any authenticated user, **When** the home screen loads, **Then** the interface renders in Arabic RTL with dark mode as default, using the project's Arabic typeface.

---

### User Story 2 - Admin Creates a Company and Users (Priority: P2)

An admin user creates a new company (tenant) in the system with both Arabic and English names. They then create user accounts under that company, assigning roles (field worker, accountant, or admin). Each user is scoped to exactly one company. The admin can view and manage all users within their company.

**Why this priority**: Multi-tenancy and user management are prerequisites for any real usage. Without companies and users, nobody can log in or submit expenses.

**Independent Test**: Can be tested by creating a company, adding users with different roles, and verifying each user can only see data within their own company.

**Acceptance Scenarios**:

1. **Given** an admin user, **When** they create a new company with name, Arabic name, and optional tax registration, **Then** the company is persisted and assigned a unique identifier.
2. **Given** an admin in Company A, **When** they create a user with role "field_worker", **Then** the user is associated with Company A and can only access Company A's data.
3. **Given** two companies (A and B), **When** an admin of Company A queries users, **Then** they see zero users from Company B — data isolation is enforced.
4. **Given** an admin, **When** they create a user, **Then** the user's password is securely hashed and never stored in plain text.

---

### User Story 3 - App Works Offline After First Load (Priority: P3)

A field worker opens the app while connected to the internet. The app shell, fonts, locale files, and static assets are cached locally. Later, in a remote area with no connectivity, the worker opens the app again. The app launches instantly from the local cache, showing the full interface with Arabic text and all navigation elements — even though there is no network.

**Why this priority**: Offline capability is a constitutional requirement and the core differentiator for field workers in remote locations. However, it depends on the app shell (P1) and auth (P1/P2) being in place first.

**Independent Test**: Can be tested by loading the app once with connectivity, then disabling the network and reloading — the app shell should render fully with all fonts and locale strings.

**Acceptance Scenarios**:

1. **Given** a user who has visited the app at least once, **When** they open the app with no network connection, **Then** the app shell loads from cache and renders the full interface.
2. **Given** an offline app load, **When** the home screen renders, **Then** Arabic fonts, locale strings, and all static assets are available from the local cache.
3. **Given** a user is offline, **When** they navigate within the app, **Then** navigation between cached screens works without errors or blank states.
4. **Given** the app is installed as a PWA, **When** the user taps the home screen icon, **Then** the app launches in standalone mode with the correct theme color and Arabic app name.

---

### User Story 4 - Database Stores Expenses with Full Audit Trail (Priority: P4)

The system maintains a database schema that can store expense records with all required fields: amount, currency, category, vendor, receipt reference, voice transcript, approval status, and AI extraction metadata. Every record is scoped to a company. The schema also supports projects (with budgets), correction feedback for AI learning, and a vendor cache for accelerating future submissions.

**Why this priority**: The data model is foundational infrastructure. While not user-facing directly, every future feature (expense capture, approval, reporting) depends on having the right schema in place.

**Independent Test**: Can be tested by inserting and querying records directly against the database, verifying all fields persist correctly, foreign keys enforce integrity, and tenant isolation prevents cross-company access.

**Acceptance Scenarios**:

1. **Given** an expense record, **When** it is created, **Then** it includes: amount, currency, category, vendor, status, timestamps, user reference, company scope, and optional fields for receipt, voice, and AI data.
2. **Given** a project under Company A, **When** an expense is linked to that project, **Then** the foreign key relationship is enforced and the project's budget is trackable.
3. **Given** an AI extraction on a receipt, **When** an accountant corrects a field, **Then** a correction feedback record is stored linking the original AI value, the corrected value, and the corrector — enabling future model improvement.
4. **Given** a vendor with a tax registration number, **When** encountered for the first time, **Then** the vendor is cached so future encounters auto-populate vendor details.

---

### User Story 5 - Bilingual Interface with Arabic Default (Priority: P5)

The entire application interface supports both Arabic and English. Arabic (Egyptian dialect) is the default language. Users can toggle to English at any time. All labels, messages, status indicators, and navigation elements are externalized and translatable. Numeric amounts always display left-to-right regardless of language direction.

**Why this priority**: While Arabic-first is a constitutional requirement, the toggle and full externalization can be layered on after the core interface exists.

**Independent Test**: Can be tested by toggling between Arabic and English and verifying all visible strings change, layout direction flips, and numeric amounts remain LTR.

**Acceptance Scenarios**:

1. **Given** the default app state, **When** the app loads, **Then** all interface text is in Arabic and the layout direction is right-to-left.
2. **Given** an Arabic interface, **When** the user toggles to English, **Then** all text switches to English, the layout direction changes to left-to-right, and numeric amounts remain LTR.
3. **Given** any language setting, **When** a monetary amount is displayed, **Then** the amount renders in left-to-right direction with monospace numeric formatting.
4. **Given** the app is offline, **When** the user toggles language, **Then** the switch works instantly because all locale files are cached locally.

---

### Edge Cases

- What happens when a user's company is deactivated while they are logged in? The session remains valid until expiry but new logins are blocked.
- What happens when the same email is used to create users in two different companies? The system rejects the second creation — email addresses are globally unique.
- What happens when the app cache is cleared by the device OS? The next online visit re-caches all assets. Offline data in the local database persists independently of the service worker cache.
- What happens if the database migration fails mid-way? The migration framework supports rollback to the previous state, ensuring no partial schema changes.
- What happens when a field worker has an extremely slow connection (2G)? The app prioritizes loading from cache, falling back to network only for data that has changed since last sync.

## Requirements

### Functional Requirements

- **FR-001**: System MUST authenticate users with email and password, returning a session token containing user identity, company scope, and role.
- **FR-002**: System MUST support three user roles: field_worker (submit expenses), accountant (review/approve expenses), and admin (manage company, users, projects).
- **FR-003**: System MUST enforce multi-tenant data isolation — every database query for tenant-scoped data MUST filter by the authenticated user's company identifier.
- **FR-004**: System MUST store passwords using a one-way cryptographic hash; plain-text passwords MUST never be persisted or logged.
- **FR-017**: System MUST lock a user account after 5 consecutive failed login attempts. The account MUST auto-unlock after 15 minutes. A calm message MUST inform the user to try again later.
- **FR-005**: System MUST provide a database schema supporting: companies, users, projects, categories, expenses, correction feedback, and vendor cache — all with timestamps and tenant scoping.
- **FR-016**: Each company MUST have an admin-configurable list of expense categories. Field workers MUST select from this predefined list when submitting expenses. AI features (in later phases) MUST suggest categories only from this list.
- **FR-006**: System MUST cache the app shell, fonts, locale files, and static assets locally so the app launches without network access after the first visit.
- **FR-007**: System MUST provide a local database on the client device for storing expense drafts and a sync queue for pending submissions.
- **FR-008**: System MUST render all interface elements in Arabic (RTL) by default, with an English (LTR) toggle.
- **FR-009**: System MUST display monetary amounts in left-to-right direction with tabular numeric formatting, regardless of interface language.
- **FR-010**: System MUST support dark mode as the default theme to reduce battery drain and improve outdoor readability.
- **FR-011**: All interactive elements MUST have touch targets of at least 44x44 CSS pixels to accommodate field workers wearing gloves.
- **FR-012**: System MUST persist user sessions locally so returning users bypass the login screen within the session validity period.
- **FR-018**: System MUST silently refresh session tokens while the user is active, preventing expiry during use. If a token expires while offline, locally cached data and drafts MUST remain accessible.
- **FR-019**: System MUST support biometric authentication (fingerprint/face via Web Authentication API) for re-login after token expiry. Email/password MUST remain available as a fallback when biometrics are unavailable.
- **FR-013**: System MUST support database schema migrations that can be applied incrementally and rolled back safely.
- **FR-014**: The app MUST be installable as a Progressive Web App with standalone display mode, correct Arabic app name, and brand theme color.
- **FR-015**: System MUST provide a CLI seed command that creates the initial company and admin user during deployment. No public self-registration is supported.

### Key Entities

- **Company**: A tenant organization. Has English and Arabic names, optional tax registration, and a settings object. All other entities are scoped to a company.
- **User**: A person within a company. Has email (globally unique), name (bilingual), hashed password, role (field_worker/accountant/admin), active status, and optional push notification subscription.
- **Project**: A cost center within a company. Has bilingual name, code, optional budget, and active status. Expenses can be linked to a project.
- **Category**: A predefined expense classification within a company. Admin-managed. Has bilingual name and active status. AI suggests from this list during expense capture (in later phases).
- **Expense**: The core record. Links to a user and optionally a project. Category is selected from the company's predefined category list. Tracks amount, currency, category, vendor, receipt, voice transcript, approval status, AI extraction data, anomaly flags, and sync state.
- **Correction Feedback**: Records accountant corrections to AI-extracted values. Links to an expense. Stores the field name, AI value, corrected value, and who corrected it. Used to improve AI accuracy over time.
- **Vendor Cache**: Caches vendor information by tax registration number. Stores vendor name (bilingual) and a category hint. Accelerates future expense submissions for known vendors.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Authenticated users reach the home screen within 3 seconds of submitting credentials on a stable connection.
- **SC-002**: The app loads from cache in under 2 seconds on repeat visits with no network connection.
- **SC-003**: All interface text is available in both Arabic and English, with zero untranslated strings visible to the user.
- **SC-004**: Data isolation is verified: queries scoped to Company A return zero records belonging to Company B, confirmed by automated checks.
- **SC-005**: The app is installable as a PWA and passes the browser's installability criteria (manifest, service worker, HTTPS-ready configuration).
- **SC-006**: All touch targets meet or exceed 44x44 CSS pixels, verified by automated audit.
- **SC-007**: The database schema supports all seven key entities (Company, User, Project, Category, Expense, Correction Feedback, Vendor Cache) with correct relationships, constraints, and indexes — verified by successful migration execution.
- **SC-008**: Dark mode renders as the default theme with sufficient contrast ratios meeting WCAG AA standards.

## Assumptions

- Users have a modern smartphone capable of running a Progressive Web App (Android 8+ or iOS 14+).
- Each user belongs to exactly one company — cross-company access is not supported.
- Email addresses are globally unique across all tenants.
- The initial deployment targets a single geographic region (Egypt) — no multi-region database replication is needed in Phase 1.
- Session tokens have a long validity period (24 hours) with silent refresh while active. Re-authentication after offline expiry uses biometric (fingerprint/face) for speed, with email/password fallback.
- The AI correction feedback schema is created in Phase 1 but the AI features that populate it are delivered in later phases.
- Font files for IBM Plex Arabic are hosted externally but cached locally by the service worker for offline use.
- The app does not need to support Internet Explorer or legacy browsers — only modern evergreen browsers.

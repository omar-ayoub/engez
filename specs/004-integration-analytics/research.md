# Research: Integration & Analytics

**Date**: 2026-05-17 | **Branch**: `004-integration-analytics`

## R1: ERP Integration Pattern

**Decision**: Adapter pattern with abstract base class (ExpenseExporter interface) and a registry dict mapping system names to adapter classes.

**Rationale**: The adapter pattern is the standard approach for multi-system integrations. A registry enables runtime selection by company config without conditional logic. Adding a new ERP = one new file implementing the interface.

**Alternatives considered**:
- Strategy pattern with DI container — over-engineered for 3 adapters
- Plugin architecture with dynamic discovery — unnecessary complexity at current scale
- Direct integration without abstraction — violates FR-001 and makes maintenance difficult

## R2: Credential Encryption Approach

**Decision**: AES-256-GCM encryption with per-company encryption keys derived from a master key via HKDF. Master key stored as environment variable (never in DB).

**Rationale**: AES-256-GCM provides authenticated encryption (integrity + confidentiality). Per-company key derivation ensures one company's compromise doesn't affect others. HKDF key derivation is standard (RFC 5869).

**Alternatives considered**:
- Application-level encryption with single key — no isolation between tenants
- Database-level encryption (pgcrypto) — harder to rotate, tied to PostgreSQL
- Vault/KMS service — good but adds infrastructure dependency for MVP

## R3: Perceptual Image Hashing

**Decision**: Average Hash (aHash) algorithm — resize to 16x16 grayscale, compare pixels to average, produce 256-bit hash. Hamming distance < 10% = "duplicate".

**Rationale**: aHash is fast (single resize + compare), sufficient for detecting re-submitted photos (same photo, possibly re-cropped or re-compressed). No ML dependency needed.

**Alternatives considered**:
- pHash (DCT-based) — more robust to transformations but slower, overkill for same-photo detection
- dHash (gradient-based) — similar performance to aHash, marginally better for rotations (not needed here)
- Neural embedding similarity — accurate but requires GPU/model serving, too heavy for MVP

## R4: Background Task Execution for Anomaly Detection

**Decision**: Use a lightweight in-process background task (FastAPI BackgroundTasks) for anomaly detection. Tasks are fire-and-forget after expense creation.

**Rationale**: At current scale (< 1000 expenses/day per company), in-process background tasks are sufficient. No need for a dedicated task queue (Celery, ARQ) yet. If the process crashes mid-detection, the expense is still saved — flags simply won't appear (graceful degradation).

**Alternatives considered**:
- Celery + Redis — adds operational complexity (worker processes, monitoring) for low volume
- ARQ (async Redis queue) — lighter than Celery but still adds a worker dependency
- Synchronous in-request — blocks field worker response by 1-3s (unacceptable for mobile UX)

## R5: Analytics Chart Library

**Decision**: Recharts 2.x — React-specific, composable, good RTL support, active maintenance.

**Rationale**: Already referenced in project phase docs. Lightweight, well-documented, supports responsive containers and custom tooltips. Arabic labels work via standard React i18n.

**Alternatives considered**:
- Chart.js + react-chartjs-2 — good but less React-native, more imperative
- Nivo — beautiful but heavier bundle, complex API
- D3 direct — too low-level for standard business charts

## R6: Excel Export Library

**Decision**: openpyxl (backend) for server-side Excel generation. CSV uses Python's built-in csv module with Arabic column headers.

**Rationale**: openpyxl is the standard Python library for .xlsx generation. Server-side generation ensures consistent output regardless of browser. The file is generated on-demand and streamed as a download response.

**Alternatives considered**:
- Frontend-only export (SheetJS) — works for CSV but Excel formatting is limited, and data must be fetched to client first
- xlsxwriter — write-only (no read), slightly faster but less feature-rich than openpyxl
- pandas to_excel — adds heavy dependency just for export

## R7: Export Retry Strategy

**Decision**: Exponential backoff with jitter: delays of 1m, 5m, 30m, 2h, 12h (5 retries over ~14.5 hours). After exhaustion, mark as permanently failed and notify admin.

**Rationale**: Exponential backoff prevents hammering a down service. Jitter prevents thundering herd when multiple exports queue up. 5 retries over ~14.5 hours covers most transient outages without excessive delay.

**Alternatives considered**:
- Linear retry (every 30 min) — wasteful for short outages, too aggressive for credential issues
- Immediate retry + circuit breaker — more complex state machine than needed
- No automatic retry — poor UX, forces manual intervention for every network blip

## R8: Zoho Books OAuth2 Token Refresh

**Decision**: Store refresh_token encrypted alongside other credentials. On 401 response, attempt token refresh automatically. If refresh fails, mark integration as "needs_reauth" and notify admin.

**Rationale**: Zoho access tokens expire every hour. Transparent refresh avoids constant admin intervention. The refresh token itself has a longer lifetime (typically 90 days) after which manual re-auth is required.

**Alternatives considered**:
- Manual token entry each time — terrible UX for hourly expiry
- Long-lived token only — Zoho doesn't support this
- Proactive refresh on schedule — adds complexity without benefit (just-in-time refresh is simpler)

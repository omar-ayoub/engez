# Feature Specification: Accountant Review Desk

**Feature Branch**: `003-review-desk`

**Created**: 2026-05-16

**Status**: Clarified

**Input**: User description: "Build the accountant review desk -- the second critical user interface that determines whether the app replaces WhatsApp or gets abandoned. The accountant sits in an office with reliable internet. They receive a queue of pending expenses submitted by field workers. For each expense, they see: the receipt image (zoomable), all AI-extracted fields with confidence indicators, the original voice transcript (if available), an ETA verification badge (if QR was decoded), and any anomaly flags. Actions: Approve (single tap), Reject with reason (required text), Edit any field (inline correction). When an accountant corrects an AI-extracted field, that correction is stored in the correction_feedback table and automatically improves future extractions for that company tenant. Bulk approve is available for expenses marked as ETA-verified with high confidence scores. Web Push notifications notify field workers of approval/rejection and notify accountants of new pending expenses (batched, not per-expense). The queue must be filterable by: project, date range, employee, status, amount range. Sort by: date, amount, project."

## Clarifications

### Session 2026-05-16

- Q: After an expense is rejected, can the field worker edit and re-submit it (same record) or must they create a new expense? → A: The field worker can edit the same rejected expense and re-submit it (status transitions from "rejected" back to "pending"), preserving full history on a single record.
- Q: Should all review actions (approve, reject, correct, bulk approve) be logged in an immutable audit trail for compliance? → A: Yes, full audit trail -- all review actions logged immutably with actor, timestamp, action type, and before/after values.
- Q: Should the review queue update in real-time (WebSockets), via polling, or manual refresh only? → A: Lightweight polling every 30 seconds -- simple, sufficient for office use, conflicts handled by optimistic concurrency (FR-028).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Expense Review Queue (Priority: P1)

An accountant opens the review desk and sees a paginated queue of pending expenses submitted by their company's field workers. Each row shows the expense amount, vendor, employee name, capture mode icon, date, and a confidence summary badge. The accountant can filter the queue by project, date range, employee, status (pending/approved/rejected), and amount range. They can sort by date, amount, or project. The queue loads quickly and updates in real-time as new expenses arrive.

**Why this priority**: The queue is the accountant's primary workspace. Without a functional, filterable queue, no review actions are possible. This is the entry point for every accountant interaction with the system.

**Independent Test**: Can be fully tested by seeding pending expenses and verifying the queue displays them with correct data, pagination works, and all filter/sort combinations return expected results.

**Acceptance Scenarios**:

1. **Given** an accountant logs in, **When** they navigate to the review desk, **Then** they see a paginated list of pending expenses for their company, sorted by newest first.
2. **Given** the review queue has 50+ expenses, **When** the accountant scrolls to the bottom, **Then** the next page loads automatically or a pagination control is available.
3. **Given** the review queue, **When** the accountant applies a project filter, **Then** only expenses for that project are shown and the result count updates.
4. **Given** the review queue, **When** the accountant applies a date range filter, **Then** only expenses within that range are shown.
5. **Given** the review queue, **When** the accountant filters by employee, **Then** only that employee's expenses appear.
6. **Given** the review queue, **When** the accountant filters by amount range, **Then** only expenses within the min/max range are shown.
7. **Given** the review queue, **When** the accountant changes the sort to "amount descending", **Then** expenses are reordered by amount from highest to lowest.

---

### User Story 2 - Expense Detail Review (Priority: P2)

An accountant taps an expense row to open the detail view. They see the receipt image (zoomable with pinch/double-tap), all AI-extracted fields with per-field confidence indicators (green >= 0.8, amber >= 0.5, red < 0.5), the original voice transcript (if voice capture was used), an ETA verification badge (if the receipt had a decoded QR code), and any anomaly flags (unusual amount, duplicate suspect, missing receipt for non-manual captures).

**Why this priority**: The detail view is where the accountant makes their judgment. Seeing all evidence (receipt, transcript, confidence, QR verification) in one screen is essential for fast, accurate decisions. Without this, approvals would be blind.

**Independent Test**: Can be tested by opening a single expense with voice transcript, receipt image, QR data, and varying confidence scores, then verifying all elements render correctly with appropriate visual indicators.

**Acceptance Scenarios**:

1. **Given** an expense with a receipt image, **When** the accountant opens the detail view, **Then** the receipt image is displayed and can be zoomed with pinch or double-tap gestures.
2. **Given** an expense with AI-extracted fields, **When** the detail view loads, **Then** each field shows a confidence badge: green for >= 0.8, amber for >= 0.5, red for < 0.5.
3. **Given** an expense captured via voice, **When** the detail view loads, **Then** the original Arabic transcript is displayed.
4. **Given** an expense with a decoded ETA QR code, **When** the detail view loads, **Then** an ETA verification badge is prominently displayed indicating the expense is tax-authority verified.
5. **Given** an expense flagged with anomalies, **When** the detail view loads, **Then** anomaly flags are visible with descriptive labels (e.g., "unusual amount", "duplicate suspect").
6. **Given** an expense without a receipt (manual entry), **When** the detail view loads, **Then** no receipt section is shown and the view gracefully adapts.

---

### User Story 3 - Approve and Reject Actions (Priority: P3)

From the detail view, the accountant can approve an expense with a single tap on a prominent approve button. They can reject an expense, but rejection requires typing a reason (minimum 5 characters). After either action, the expense disappears from the pending queue and the accountant is taken to the next pending expense or back to the queue if none remain. The field worker is notified of the decision via Web Push notification.

**Why this priority**: Approve/reject is the core action that moves expenses through the workflow. This is the fundamental value proposition of the review desk -- replacing the WhatsApp back-and-forth with structured, auditable decisions.

**Independent Test**: Can be tested by approving and rejecting expenses, verifying status changes persist, rejection reasons are stored, and the queue updates to exclude actioned items.

**Acceptance Scenarios**:

1. **Given** a pending expense in detail view, **When** the accountant taps "Approve", **Then** the expense status changes to "approved" and it is removed from the pending queue.
2. **Given** a pending expense in detail view, **When** the accountant taps "Reject", **Then** a reason input appears and the reject action is disabled until a reason of at least 5 characters is provided.
3. **Given** a rejected expense, **When** the rejection is confirmed, **Then** the rejection reason is stored with the expense and visible in the expense history.
4. **Given** an expense is approved or rejected, **When** the action completes, **Then** the view navigates to the next pending expense or returns to the queue if none remain.
5. **Given** an expense is approved or rejected, **When** the action completes, **Then** the field worker who submitted the expense receives a Web Push notification with the decision (and reason, if rejected).

---

### User Story 4 - Inline Field Correction (Priority: P4)

The accountant can tap any AI-extracted field in the detail view to edit it inline. When they change a value, the correction is saved to the expense and simultaneously stored in the correction_feedback table, recording the AI's original value, the corrected value, the corrector, and the field name. These corrections accumulate per company and are fed back into AI extraction prompts, progressively improving accuracy for that tenant.

**Why this priority**: The correction feedback loop is the "compounding moat" -- the more an accountant uses the system, the smarter it becomes for their company. This creates switching costs and long-term value that competitors cannot replicate.

**Independent Test**: Can be tested by editing an AI-extracted field, verifying the expense updates, a correction_feedback record is created, and the original AI value is preserved in the feedback.

**Acceptance Scenarios**:

1. **Given** an expense with AI-extracted fields in detail view, **When** the accountant taps a field value, **Then** an inline editor appears allowing the accountant to change the value.
2. **Given** an inline edit, **When** the accountant confirms the new value, **Then** the expense field is updated and a correction_feedback record is created with the original AI value, the corrected value, the field name, and the corrector's identity.
3. **Given** an expense without AI extraction (manual entry), **When** the accountant views the detail, **Then** fields are editable but no correction_feedback is generated (since there is no AI value to compare against).
4. **Given** multiple corrections across many expenses, **When** the system processes a new AI extraction for the same company, **Then** the correction history is used to improve extraction accuracy via few-shot examples.

---

### User Story 5 - Bulk Approve (Priority: P5)

The accountant can select multiple expenses from the queue and approve them all at once. Bulk approve is only available for expenses that are ETA-verified (QR-decoded) and have high confidence scores (all fields >= 0.8). The bulk approve button shows a count of selected items. Non-eligible expenses cannot be selected for bulk action. After bulk approval, all affected field workers are notified.

**Why this priority**: Bulk approve accelerates the accountant's workflow for high-confidence, verified expenses. It is an efficiency optimization that becomes valuable once the queue is functional and individual review works.

**Independent Test**: Can be tested by seeding a mix of ETA-verified high-confidence expenses and non-verified ones, selecting eligible items, bulk approving, and verifying only eligible items were approved.

**Acceptance Scenarios**:

1. **Given** the review queue, **When** the accountant enables selection mode, **Then** checkboxes appear next to expenses that are ETA-verified and have all confidence scores >= 0.8.
2. **Given** non-eligible expenses (not ETA-verified or low confidence), **When** selection mode is active, **Then** those expenses cannot be selected (checkboxes are disabled or absent).
3. **Given** selected eligible expenses, **When** the accountant taps "Bulk Approve", **Then** all selected expenses are approved in one action and the queue updates.
4. **Given** a bulk approve action, **When** the action completes, **Then** each affected field worker receives a Web Push notification for their approved expense(s).

---

### User Story 6 - Web Push Notifications (Priority: P6)

Field workers receive Web Push notifications when their expenses are approved or rejected. Accountants receive batched notifications when new pending expenses arrive (e.g., "5 new expenses pending review"), aggregated to avoid notification spam. Push subscription is managed via the browser's Push API with VAPID authentication. Users can opt in/out of notifications.

**Why this priority**: Notifications close the communication loop that currently happens over WhatsApp. They are essential for the app to fully replace the existing workflow, but depend on all review actions (P3-P5) being functional first.

**Independent Test**: Can be tested by approving/rejecting an expense and verifying the field worker receives a push notification, and by submitting new expenses and verifying the accountant receives a batched notification.

**Acceptance Scenarios**:

1. **Given** a field worker has granted push notification permission, **When** their expense is approved, **Then** they receive a push notification with the expense amount and approval status in Arabic.
2. **Given** a field worker has granted push notification permission, **When** their expense is rejected, **Then** they receive a push notification with the expense amount, rejection status, and the rejection reason in Arabic.
3. **Given** an accountant has granted push notification permission, **When** new expenses are synced to the server, **Then** the accountant receives a batched notification (e.g., "5 new expenses pending review"), not one per expense.
4. **Given** a user has not granted push notification permission, **When** an event occurs, **Then** no push notification is sent and no error occurs.
5. **Given** the push subscription has expired, **When** a notification send fails, **Then** the system silently handles the failure without disrupting the workflow.

---

### User Story 7 - AI Correction Metrics (Priority: P7)

An admin can view AI correction metrics for their company: total expenses processed, correction counts per field (amount, vendor, category, items, etc.), and correction rate trends. This helps the admin understand which fields the AI struggles with and track improvement over time.

**Why this priority**: Metrics provide visibility into the compounding moat's progress. They are a management feature that adds value once a meaningful volume of corrections has been collected.

**Independent Test**: Can be tested by creating correction_feedback records and verifying the metrics endpoint returns accurate counts grouped by field name.

**Acceptance Scenarios**:

1. **Given** an admin user, **When** they navigate to the AI metrics view, **Then** they see total expenses processed and correction counts per field for their company.
2. **Given** correction_feedback records exist, **When** the metrics load, **Then** fields with the highest correction counts are highlighted to indicate areas needing AI improvement.
3. **Given** a non-admin user, **When** they attempt to access the metrics view, **Then** access is denied.

---

### Edge Cases

- What happens when an accountant tries to approve an already-approved expense (e.g., via a stale browser tab)? The system should return an error indicating the expense has already been actioned, and refresh the queue.
- What happens when two accountants try to approve/reject the same expense simultaneously? The first action should succeed; the second should see a conflict error and be asked to refresh.
- What happens when the accountant applies filters that return zero results? The queue should show an empty state with a clear message and a suggestion to adjust filters.
- What happens when a receipt image fails to load (e.g., R2 signed URL expired)? The detail view should show a placeholder with a "retry" button that generates a fresh signed URL.
- What happens when the correction_feedback table grows very large (10,000+ records per company)? The few-shot example query should be optimized with limits and recency weighting.
- What happens when a field worker has no push subscription registered? Notification send is silently skipped; no error is surfaced to the accountant.
- What happens when bulk approve is attempted with an empty selection? The bulk approve button should be disabled when no items are selected.
- What happens when an accountant tries to reject without providing a reason? The reject confirmation is disabled until a reason of at least 5 characters is entered.
- What happens when a field worker re-submits a previously rejected expense? The expense status transitions from "rejected" to "pending" and reappears in the accountant's queue. The previous rejection reason remains in the history for context.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a paginated review queue showing pending expenses scoped to the accountant's company.
- **FR-002**: System MUST support filtering the queue by: project, date range, employee, status (pending/approved/rejected), and amount range (min/max).
- **FR-003**: System MUST support sorting the queue by: date (default, newest first), amount, and project.
- **FR-004**: System MUST display per-expense summary in the queue row: amount, vendor, employee name, capture mode, date, and confidence summary.
- **FR-005**: System MUST provide an expense detail view showing all AI-extracted fields with per-field confidence indicators using a three-tier color system (green >= 0.8, amber >= 0.5, red < 0.5).
- **FR-006**: System MUST display a zoomable receipt image in the detail view (pinch-to-zoom and double-tap-to-zoom).
- **FR-007**: System MUST display the original voice transcript in the detail view when the expense was captured via voice or combined mode.
- **FR-008**: System MUST display an ETA verification badge when the expense has QR-decoded data.
- **FR-009**: System MUST display anomaly flags on expenses with unusual characteristics (unusual amount relative to company history, duplicate suspect, missing receipt for non-manual captures).
- **FR-010**: System MUST allow single-tap approval of a pending expense, changing its status to "approved".
- **FR-011**: System MUST allow rejection of a pending expense, requiring a text reason of at least 5 characters before the rejection is confirmed.
- **FR-012**: System MUST store the rejection reason with the expense record.
- **FR-013**: System MUST allow inline editing of any AI-extracted field on a pending expense.
- **FR-014**: System MUST create a correction_feedback record when an AI-extracted field is corrected, storing: expense ID, company ID, field name, original AI value, corrected value, and corrector identity.
- **FR-015**: System MUST NOT create correction_feedback records when editing fields on manually-entered expenses (no AI value to compare).
- **FR-016**: System MUST support bulk approval of multiple expenses in a single action.
- **FR-017**: Bulk approve MUST only be available for expenses that are ETA-verified AND have all AI confidence scores >= 0.8.
- **FR-018**: System MUST send a Web Push notification to the field worker when their expense is approved or rejected, including the amount, status, and rejection reason (if applicable) in Arabic.
- **FR-019**: System MUST send batched Web Push notifications to accountants when new pending expenses arrive, aggregating the count rather than sending per-expense.
- **FR-020**: System MUST manage push subscriptions via the Web Push API with VAPID authentication.
- **FR-021**: System MUST allow users to subscribe to and unsubscribe from push notifications.
- **FR-022**: System MUST handle expired or invalid push subscriptions gracefully without disrupting the workflow.
- **FR-023**: System MUST provide an AI correction metrics endpoint showing total expenses and correction counts grouped by field name, scoped to the requesting user's company.
- **FR-024**: System MUST restrict review queue access to users with "accountant" or "admin" roles.
- **FR-025**: System MUST restrict AI metrics access to users with "admin" role.
- **FR-026**: System MUST scope all queries to the authenticated user's company (multi-tenant isolation).
- **FR-027**: System MUST navigate to the next pending expense after an approve/reject action, or return to the queue if no pending expenses remain.
- **FR-028**: System MUST prevent duplicate actions on the same expense (optimistic concurrency -- if the expense was already actioned, show an error).
- **FR-029**: System MUST allow field workers to edit a rejected expense and re-submit it, transitioning the status from "rejected" back to "pending" on the same record, preserving the full review history.
- **FR-030**: System MUST log all review actions (approve, reject, correct, bulk approve) in an immutable audit trail recording: actor identity, timestamp, action type, expense ID, and before/after values for any changed fields.
- **FR-031**: Audit trail records MUST NOT be editable or deletable once created.
- **FR-032**: System MUST auto-refresh the review queue every 30 seconds via lightweight polling to reflect changes made by other accountants or newly synced expenses.
- **FR-033**: If an expense in the queue was actioned by another accountant since last refresh, the system MUST show a conflict notification when the current accountant attempts to action it.

### Key Entities

- **Expense** (existing): The financial record under review. Key review-relevant fields: status (pending/approved/rejected), rejection_reason, ai_extraction (JSONB), ai_confidence (JSONB), anomaly_flags (JSONB), eta_verified (boolean), receipt_url, voice_transcript, capture_mode.
- **CorrectionFeedback** (existing): Records accountant corrections to AI-extracted fields. Fields: expense_id, company_id, field_name, ai_value, corrected_value, corrected_by. Used to generate few-shot examples that improve AI accuracy per tenant.
- **User** (existing): The accountant or admin performing reviews, and the field worker receiving notifications. Key fields: role, push_subscription (JSONB).
- **Push Subscription**: A browser-generated VAPID subscription object stored in the User record, used to deliver Web Push notifications.
- **Anomaly Flag**: A computed flag attached to an expense indicating unusual characteristics. Stored in the anomaly_flags JSONB column. Types: unusual_amount (amount exceeds 3x company average), duplicate_suspect (same amount + vendor + date within 24 hours), missing_receipt (non-manual capture with no receipt_url).
- **Review Audit Log** (new): An immutable record of every review action taken on an expense. Fields: expense_id, actor_id, company_id, action_type (approve/reject/correct/bulk_approve/resubmit), field_name (for corrections), value_before, value_after, rejection_reason (for rejections), timestamp. Records are append-only and cannot be edited or deleted.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Accountants can review and action (approve/reject) an expense in under 30 seconds from opening the detail view.
- **SC-002**: The review queue loads within 2 seconds for up to 1,000 pending expenses per company.
- **SC-003**: Bulk approve processes up to 50 expenses in a single action within 3 seconds.
- **SC-004**: Field workers receive push notifications for expense decisions within 10 seconds of the accountant's action.
- **SC-005**: 100% of AI field corrections are stored in the correction_feedback table with complete data (original value, corrected value, field name, corrector).
- **SC-006**: Zero cross-tenant data leakage -- accountants see only their company's expenses.
- **SC-007**: The correction feedback loop demonstrably improves AI extraction accuracy after 50+ corrections per company (measured via the AI metrics endpoint).
- **SC-008**: Filter and sort operations on the queue respond within 1 second for datasets up to 10,000 expenses.
- **SC-009**: Push notification delivery achieves 95%+ success rate for active, valid subscriptions.
- **SC-010**: The review desk is fully functional in Arabic RTL layout with all labels, notifications, and UI elements properly localized.

## Assumptions

- Accountants work in an office environment with reliable internet connectivity; offline support for the review desk is not required.
- The existing Expense, CorrectionFeedback, User, and related models from Phase 2 are available and will be extended as needed (not rewritten).
- Push notification permission will be requested after the accountant's first successful review action, not on page load (to avoid permission fatigue).
- Anomaly detection rules (unusual amount, duplicate suspect, missing receipt) are computed at expense sync time and stored in the anomaly_flags JSONB column, not computed on-the-fly during review.
- The batched accountant notification ("N expenses pending") is triggered by a periodic check (e.g., every 5 minutes) or on a threshold (e.g., when 5+ new expenses have arrived since last notification), not per-expense.
- The ETA verification badge relies on QR data already decoded during Phase 2 capture; the review desk does not re-decode QR codes.
- The receipt image is served via Cloudflare R2 signed URLs with a configurable expiration; the frontend handles URL refresh if the image fails to load.
- The review desk is a desktop-optimized view (the accountant's office context), but must remain functional on tablet form factors.

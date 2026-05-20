# UI Contract: Accountant Review Desk

## Routes

| Route | Roles | Purpose |
|-------|-------|---------|
| `/review` | accountant, admin | Review queue with filters, sort, pagination/infinite loading, bulk approve. |
| `/review/:expenseId` | accountant, admin | Expense evidence detail, receipt zoom, transcript, ETA badge, anomalies, approve/reject/correct. |
| `/review/metrics` | admin | AI correction metrics for the current company. |

Unauthorized users are redirected to `/` with a localized access-denied toast or inline state.

## Review Queue Page

Required visible controls:
- Project filter
- Date range filter
- Employee filter
- Status filter
- Amount min/max filter
- Sort by date, amount, project
- Sort direction
- Selection mode for bulk approve

Required row content:
- Amount in LTR tabular numeric formatting
- Vendor
- Employee name
- Capture mode icon with accessible label
- Date
- Project label when present
- Confidence summary badge
- ETA verification badge when true
- Anomaly count/labels when present
- Disabled or absent bulk checkbox when not eligible

Polling:
- Fetch queue immediately on route load.
- Poll every 30 seconds while tab is visible.
- Pause polling while tab is hidden.
- Manual refresh remains available.
- If offline, render the most recent cached queue for the active filters and show pending-sync indicators for local outbox actions.

Empty states:
- No matching results: tell user to adjust filters.
- No pending expenses: quiet empty state, no warning styling.
- Offline with no cache: explain that the queue will load when connection returns.

## Expense Detail Page

Required sections:
- Receipt viewer when `receipt_url` exists
- AI-extracted fields with per-field confidence badges
- Inline field editors for editable fields
- Original voice transcript when present
- ETA verification badge when present
- Anomaly flags with labels
- Audit timeline
- Approve action
- Reject action with required reason dialog

Receipt viewer:
- Supports zoom, pan, and double-tap zoom.
- On image load failure, calls `POST /api/v1/expenses/{id}/receipt-url` once before showing an error state.
- Does not expose public receipt URLs.

Action behavior:
- Approve is one tap from detail.
- Reject opens a reason dialog; confirm disabled until trimmed reason length >= 5.
- Correct writes local outbox item before calling the API.
- After approve/reject success, navigate to `next_pending_id` when present; otherwise return to `/review`.
- On HTTP 409, refresh detail and show a localized conflict message.

Offline behavior:
- Approve/reject/correct/bulk actions are recorded in Dexie `reviewActions` first.
- Pending actions show a non-alarming pending confirmation state.
- Field-worker push notifications are not implied until server confirmation.
- Conflicted outbox items remain visible for manual resolution.

## Bulk Approve

Selection rules:
- Only rows with `bulk_eligible = true` can be selected.
- Button label includes selected count.
- Button disabled for zero selected items.
- Request cap is 50 selected items.

After completion:
- Approved rows are removed from pending queue.
- Skipped/ineligible rows remain and show a concise reason.
- Conflicts trigger refresh and remain unselected.

## AI Metrics Page

Admin-only view:
- Total expenses processed
- Total AI expenses
- Total corrections
- Correction rate
- Counts by field
- Daily trend
- Highlight fields with the highest correction counts

Non-admin behavior:
- Access denied state, no metrics request body or cached metrics displayed.

## RTL, Accessibility, and Visual Rules

- Default language and layout are Arabic RTL.
- All strings live in `src/locales/ar/review.json` and `src/locales/en/review.json`.
- Use CSS logical properties for spacing and layout.
- Amounts use `dir="ltr"` and tabular nums.
- Touch targets are at least 44x44 CSS pixels.
- Status indicators include icon/text labels, not color alone.
- No nested cards and no decorative illustrations on review screens.
- Respect `prefers-reduced-motion`.

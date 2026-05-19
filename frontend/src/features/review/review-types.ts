export type ReviewStatus = "pending" | "approved" | "rejected";

export type CaptureMode = "voice" | "receipt" | "combined" | "manual";

export type ReviewActionType = "approve" | "reject" | "correct" | "bulk_approve" | "resubmit";

export interface ConfidenceSummary {
  min: number;
  all_high: boolean;
  low_count: number;
  fields?: Record<string, number>;
}

export interface ReviewQueueItem {
  id: string;
  review_version: number;
  status: ReviewStatus;
  amount: number;
  currency: string;
  vendor: string | null;
  employee: { id: string; name: string; name_ar: string };
  project: { id: string; name: string; name_ar: string; code: string } | null;
  capture_mode: CaptureMode;
  created_at: string;
  eta_verified: boolean;
  confidence_summary: ConfidenceSummary | null;
  anomaly_count: number;
  bulk_eligible: boolean;
}

export interface ReviewQueueResponse {
  items: ReviewQueueItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  server_time: string;
}

export interface ReviewQueueFilters {
  status?: string;
  project_id?: string;
  employee_id?: string;
  date_from?: string;
  date_to?: string;
  amount_min?: number;
  amount_max?: number;
  sort_by?: "date" | "amount" | "project";
  sort_order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export interface EmployeeInfo {
  id: string;
  name: string;
  name_ar: string;
}

export interface AuditHistoryItem {
  id: string;
  action_type: string;
  actor_id: string;
  field_name: string | null;
  value_before: Record<string, unknown> | null;
  value_after: Record<string, unknown> | null;
  rejection_reason: string | null;
  created_at: string;
}

export interface ETAInfo {
  verified: boolean;
  uuid: string | null;
  vendor_tax_reg: string | null;
}

export interface ReviewDetailResponse {
  id: string;
  review_version: number;
  status: ReviewStatus;
  amount: number;
  currency: string;
  vendor: string | null;
  vendor_tax_reg: string | null;
  items: string;
  notes: string | null;
  category_id: string | null;
  project_id: string | null;
  capture_mode: CaptureMode;
  receipt_url: string | null;
  voice_transcript: string | null;
  eta: ETAInfo | null;
  ai_extraction: Record<string, unknown> | null;
  ai_confidence: Record<string, number> | null;
  anomaly_flags: Record<string, unknown> | null;
  employee: EmployeeInfo;
  audit_history: AuditHistoryItem[];
  created_at: string;
  updated_at: string;
}

export interface ApproveRejectResponse {
  id: string;
  status: ReviewStatus;
  review_version: number;
  rejection_reason?: string | null;
  reviewed_at: string;
  next_pending_id: string | null;
}

export interface CorrectExpenseRequest {
  review_version: number;
  field_name: string;
  corrected_value: string | number;
}

export interface CorrectExpenseResponse {
  id: string;
  review_version: number;
  field_name: string;
  value_before: string;
  value_after: string;
  correction_feedback_created: boolean;
  correction_feedback_id: string | null;
}

export interface BulkApproveRequest {
  items: Array<{ id: string; review_version: number }>;
}

export interface BulkSkippedItem {
  id: string;
  reason: string;
}

export interface BulkConflictItem {
  id: string;
  reason: string;
}

export interface BulkApproveResponse {
  bulk_operation_id: string;
  approved: number;
  approved_ids: string[];
  skipped: BulkSkippedItem[];
  conflicts: BulkConflictItem[];
}

export interface ReceiptUrlResponse {
  receipt_url: string;
  expires_in: number;
}

export interface CorrectionFieldMetric {
  field_name: string;
  count: number;
  rate: number;
}

export interface DailyCorrectionTrend {
  date: string;
  corrections: number;
  ai_expenses: number;
}

export interface AiMetricsResponse {
  total_expenses: number;
  total_ai_expenses: number;
  total_corrections: number;
  correction_rate: number;
  corrections_by_field: CorrectionFieldMetric[];
  daily_trend: DailyCorrectionTrend[];
}

export interface ReviewActionOutboxItem {
  id: string;
  companyId: string;
  expenseId?: string;
  type: ReviewActionType;
  payload: string;
  reviewVersion?: number;
  status: "pending" | "syncing" | "conflict" | "failed";
  retryCount: number;
  createdAt: Date;
  lastAttempt?: Date;
  error?: string;
}

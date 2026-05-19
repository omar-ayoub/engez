import { api, ApiConflictError, ApiError } from "@/lib/api";
import type {
  ReviewQueueResponse,
  ReviewQueueFilters,
  ReviewDetailResponse,
  ReceiptUrlResponse,
  ApproveRejectResponse,
  CorrectExpenseResponse,
  BulkApproveResponse,
  BulkApproveRequest,
  AiMetricsResponse,
} from "./review-types";

export { ApiConflictError, ApiError };

export async function fetchReviewQueue(filters: ReviewQueueFilters): Promise<ReviewQueueResponse> {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.project_id) params.set("project_id", filters.project_id);
  if (filters.employee_id) params.set("employee_id", filters.employee_id);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  if (filters.amount_min !== undefined) params.set("amount_min", String(filters.amount_min));
  if (filters.amount_max !== undefined) params.set("amount_max", String(filters.amount_max));
  if (filters.sort_by) params.set("sort_by", filters.sort_by);
  if (filters.sort_order) params.set("sort_order", filters.sort_order);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));

  return api.get(`/api/v1/expenses/queue?${params.toString()}`);
}

export async function fetchReviewDetail(expenseId: string): Promise<ReviewDetailResponse> {
  return api.get(`/api/v1/expenses/${expenseId}/review-detail`);
}

export async function refreshReceiptUrl(expenseId: string): Promise<ReceiptUrlResponse> {
  return api.post(`/api/v1/expenses/${expenseId}/receipt-url`);
}

export async function approveExpense(expenseId: string, reviewVersion: number): Promise<ApproveRejectResponse> {
  return api.post(`/api/v1/expenses/${expenseId}/approve`, { review_version: reviewVersion });
}

export async function rejectExpense(
  expenseId: string,
  reviewVersion: number,
  reason: string
): Promise<ApproveRejectResponse> {
  return api.post(`/api/v1/expenses/${expenseId}/reject`, { review_version: reviewVersion, reason });
}

export async function correctExpense(
  expenseId: string,
  reviewVersion: number,
  fieldName: string,
  correctedValue: string | number
): Promise<CorrectExpenseResponse> {
  return api.post(`/api/v1/expenses/${expenseId}/correct`, {
    review_version: reviewVersion,
    field_name: fieldName,
    corrected_value: correctedValue,
  });
}

export async function bulkApprove(req: BulkApproveRequest): Promise<BulkApproveResponse> {
  return api.post("/api/v1/expenses/bulk-approve", req);
}

export async function fetchAiMetrics(dateFrom?: string, dateTo?: string): Promise<AiMetricsResponse> {
  const params = new URLSearchParams();
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  const qs = params.toString();
  return api.get(`/api/v1/expenses/ai-metrics${qs ? `?${qs}` : ""}`);
}

export async function fetchVapidPublicKey(): Promise<string> {
  const data = await api.get<{ public_key: string }>("/api/v1/notifications/vapid-public-key");
  return data.public_key;
}

export async function subscribePush(subscription: PushSubscriptionJSON): Promise<void> {
  await api.put("/api/v1/notifications/subscription", subscription);
}

export async function unsubscribePush(): Promise<void> {
  await api.delete("/api/v1/notifications/subscription");
}

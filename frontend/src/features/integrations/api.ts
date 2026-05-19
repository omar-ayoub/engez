import { api } from "@/lib/api";

const BASE = "/api/v1/integrations";

export function getAvailable() {
  return api.get<Array<{ system_name: string; display_name: string; display_name_ar: string; required_fields: string[] }>>(
    `${BASE}/available`,
  );
}

export function configure(data: { system_name: string; credentials: Record<string, string>; field_mappings?: Record<string, unknown> }) {
  return api.post<{ system_name: string; status: string }>(`${BASE}/configure`, data);
}

export function testConnection(data: { system_name: string; credentials: Record<string, string> }) {
  return api.post<{ success: boolean; message: string }>(`${BASE}/test-connection`, data);
}

export function getStatus() {
  return api.get<{ configured: boolean; system_name?: string; status?: string; last_sync_at?: string; last_error?: string }>(
    `${BASE}/status`,
  );
}

export function getExports(params?: { status?: string; page?: number }) {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.page) qs.set("page", String(params.page));
  return api.get<{ items: Array<{ id: string; expense_id: string; system_name: string; status: string; external_ref_id: string | null; attempt_count: number; created_at: string }>; total: number; page: number; page_size: number }>(
    `${BASE}/exports?${qs}`,
  );
}

export function retryExport(expenseId: string) {
  return api.post<{ export_id: string; status: string }>(`${BASE}/export/${expenseId}/retry`);
}

export function getCsvExportUrl(dateFrom: string, dateTo: string) {
  return `${BASE}/csv-export?date_from=${dateFrom}&date_to=${dateTo}`;
}

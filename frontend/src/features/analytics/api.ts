import { api } from "@/lib/api";

const BASE = "/api/v1/analytics";

export function fetchSpendByProject(days = 30) {
  return api.get<Array<{ name: string; name_ar: string; budget: number | null; total_spend: number; expense_count: number }>>(
    `${BASE}/spend-by-project?days=${days}`,
  );
}

export function fetchSpendByCategory(days = 30) {
  return api.get<Array<{ category: string; category_ar: string; total: number; count: number }>>(
    `${BASE}/spend-by-category?days=${days}`,
  );
}

export function fetchSpendTrend(days = 90) {
  return api.get<Array<{ week: string; total: number; count: number }>>(
    `${BASE}/spend-trend?days=${days}`,
  );
}

export function fetchBudgetVsActual() {
  return api.get<Array<{ name: string; name_ar: string; budget: number | null; actual_spend: number }>>(
    `${BASE}/budget-vs-actual`,
  );
}

export function fetchSummary(days = 30) {
  return api.get<{ total_spend: number; expense_count: number; project_count: number; period_days: number }>(
    `${BASE}/summary?days=${days}`,
  );
}

export function getExportUrl(format: string, view: string, days = 30) {
  return `${BASE}/export?format=${format}&view=${view}&days=${days}`;
}

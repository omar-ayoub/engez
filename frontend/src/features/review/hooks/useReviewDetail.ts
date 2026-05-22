import { useState, useEffect, useCallback } from "react";
import { fetchReviewDetail, refreshReceiptUrl } from "../review-api";
import { db } from "@/lib/db";
import { useAuthStore } from "@/lib/auth";
import type { ReviewDetailResponse } from "../review-types";

export function useReviewDetail(expenseId: string) {
  const [data, setData] = useState<ReviewDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDetail = useCallback(async () => {
    try {
      const detail = await fetchReviewDetail(expenseId);
      setData(detail);
      setError(null);

      const companyId = useAuthStore.getState().user?.company_id || "unknown";
      await db.reviewDetailCache.put({
        expenseId,
        companyId,
        payload: JSON.stringify(detail),
        fetchedAt: new Date(),
      });
    } catch (err) {
      const cached = await db.reviewDetailCache.get(expenseId);
      if (cached) {
        setData(JSON.parse(cached.payload));
      } else {
        setError(err instanceof Error ? err.message : "Failed to load detail");
      }
    } finally {
      setLoading(false);
    }
  }, [expenseId]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  const handleReceiptRefresh = useCallback(async () => {
    if (!expenseId) return;
    try {
      const result = await refreshReceiptUrl(expenseId);
      setData((prev) => prev ? { ...prev, receipt_url: result.receipt_url } : prev);
    } catch { /* receipt refresh is best-effort */ }
  }, [expenseId]);

  const handleReceiptError = useCallback(() => {
    handleReceiptRefresh();
  }, [handleReceiptRefresh]);

  return { data, setData, loading, error, refresh: loadDetail, handleReceiptRefresh, handleReceiptError };
}

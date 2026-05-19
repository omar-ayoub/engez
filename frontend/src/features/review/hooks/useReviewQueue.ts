import { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams } from "react-router";
import { fetchReviewQueue } from "../review-api";
import { db } from "@/lib/db";
import { useAuthStore } from "@/lib/auth";
import { drainReviewOutbox, getPendingReviewActions, getConflictReviewActions } from "@/lib/review-sync";
import type { ReviewQueueResponse, ReviewQueueFilters } from "../review-types";

export function useReviewQueue() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<ReviewQueueResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [pendingCount, setPendingCount] = useState(0);
  const [conflictCount, setConflictCount] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const filters: ReviewQueueFilters = {
    status: searchParams.get("status") || "pending",
    project_id: searchParams.get("project_id") || undefined,
    employee_id: searchParams.get("employee_id") || undefined,
    date_from: searchParams.get("date_from") || undefined,
    date_to: searchParams.get("date_to") || undefined,
    amount_min: searchParams.get("amount_min") ? Number(searchParams.get("amount_min")) : undefined,
    amount_max: searchParams.get("amount_max") ? Number(searchParams.get("amount_max")) : undefined,
    sort_by: (searchParams.get("sort_by") as ReviewQueueFilters["sort_by"]) || "date",
    sort_order: (searchParams.get("sort_order") as ReviewQueueFilters["sort_order"]) || "desc",
    page: searchParams.get("page") ? Number(searchParams.get("page")) : 1,
    page_size: searchParams.get("page_size") ? Number(searchParams.get("page_size")) : 25,
  };

  const updateFilters = useCallback((updates: Partial<ReviewQueueFilters>) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      for (const [key, value] of Object.entries(updates)) {
        if (value === undefined || value === null || value === "") {
          next.delete(key);
        } else {
          next.set(key, String(value));
        }
      }
      return next;
    });
  }, [setSearchParams]);

  const loadQueue = useCallback(async () => {
    try {
      const response = await fetchReviewQueue(filters);
      setData(response);
      setError(null);

      const cacheKey = JSON.stringify(filters);
      const companyId = useAuthStore.getState().user?.company_id || "unknown";
      await db.reviewQueueCache.put({
        key: cacheKey,
        companyId,
        payload: JSON.stringify(response),
        fetchedAt: new Date(),
      });
    } catch (err) {
      const cacheKey = JSON.stringify(filters);
      const cached = await db.reviewQueueCache.get(cacheKey);
      if (cached) {
        setData(JSON.parse(cached.payload));
        setIsOffline(true);
      } else {
        setError(err instanceof Error ? err.message : "Failed to load queue");
      }
    } finally {
      setLoading(false);
    }
  }, [searchParams]);

  const loadOutboxCounts = useCallback(async () => {
    const pending = await getPendingReviewActions();
    const conflicts = await getConflictReviewActions();
    setPendingCount(pending.length);
    setConflictCount(conflicts.length);
  }, []);

  useEffect(() => {
    loadQueue();
    loadOutboxCounts();
  }, [loadQueue, loadOutboxCounts]);

  useEffect(() => {
    const startPolling = () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = setInterval(() => {
        if (document.visibilityState === "visible" && navigator.onLine) {
          loadQueue();
          drainReviewOutbox();
          loadOutboxCounts();
        }
      }, 30_000);
    };

    startPolling();

    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        loadQueue();
      }
    };

    const handleOnline = () => {
      setIsOffline(false);
      loadQueue();
      drainReviewOutbox();
      loadOutboxCounts();
    };
    const handleOffline = () => setIsOffline(true);

    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [loadQueue, loadOutboxCounts]);

  return {
    data,
    loading,
    error,
    isOffline,
    filters,
    updateFilters,
    refresh: loadQueue,
    pendingCount,
    conflictCount,
  };
}

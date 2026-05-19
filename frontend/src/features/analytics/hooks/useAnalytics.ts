import { useState, useEffect, useCallback } from "react";
import {
  fetchSpendByProject,
  fetchSpendByCategory,
  fetchSpendTrend,
  fetchBudgetVsActual,
  fetchSummary,
} from "../api";

type PeriodDays = 7 | 30 | 90 | 365;

interface AnalyticsState {
  spendByProject: Awaited<ReturnType<typeof fetchSpendByProject>> | null;
  spendByCategory: Awaited<ReturnType<typeof fetchSpendByCategory>> | null;
  spendTrend: Awaited<ReturnType<typeof fetchSpendTrend>> | null;
  budgetVsActual: Awaited<ReturnType<typeof fetchBudgetVsActual>> | null;
  summary: Awaited<ReturnType<typeof fetchSummary>> | null;
  loading: boolean;
  error: string | null;
  period: PeriodDays;
  setPeriod: (days: PeriodDays) => void;
  refresh: () => void;
}

export function useAnalytics(): AnalyticsState {
  const [period, setPeriod] = useState<PeriodDays>(30);
  const [spendByProject, setSpendByProject] = useState<AnalyticsState["spendByProject"]>(null);
  const [spendByCategory, setSpendByCategory] = useState<AnalyticsState["spendByCategory"]>(null);
  const [spendTrend, setSpendTrend] = useState<AnalyticsState["spendTrend"]>(null);
  const [budgetVsActual, setBudgetVsActual] = useState<AnalyticsState["budgetVsActual"]>(null);
  const [summaryData, setSummaryData] = useState<AnalyticsState["summary"]>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const [proj, cat, trend, budget, sum] = await Promise.all([
          fetchSpendByProject(period),
          fetchSpendByCategory(period),
          fetchSpendTrend(period),
          fetchBudgetVsActual(),
          fetchSummary(period),
        ]);
        if (cancelled) return;
        setSpendByProject(proj);
        setSpendByCategory(cat);
        setSpendTrend(trend);
        setBudgetVsActual(budget);
        setSummaryData(sum);
        setError(null);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [period, refreshKey]);

  return {
    spendByProject,
    spendByCategory,
    spendTrend,
    budgetVsActual,
    summary: summaryData,
    loading,
    error,
    period,
    setPeriod,
    refresh,
  };
}

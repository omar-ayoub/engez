import { useState, useEffect, useCallback } from "react";
import { fetchAiMetrics } from "../review-api";
import type { AiMetricsResponse } from "../review-types";

export function useAiMetrics() {
  const [data, setData] = useState<AiMetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const metrics = await fetchAiMetrics();
      setData(metrics);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load metrics");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { data, loading, error, refresh: load };
}

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/lib/auth";

interface Metrics {
  total_flags: number;
  by_type: Record<string, number>;
  avg_flags_per_expense: number;
  rejection_correlation: number;
  period_days: number;
}

const TYPE_KEYS = ["duplicate_receipt", "statistical_outlier", "high_velocity", "vendor_mismatch"] as const;

export default function AnomalyMetrics() {
  const { t } = useTranslation("integrations");
  const accessToken = useAuthStore((s) => s.accessToken);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    fetch("/api/v1/anomalies/metrics?days=30", {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error(t("anomaly.fetchError"));
        return res.json();
      })
      .then((data) => setMetrics(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [accessToken, t]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
        <p className="text-muted-foreground">{t("loading")}</p>
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center gap-2">
        <p className="text-destructive">{error || t("anomaly.fetchError")}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-4xl mx-auto px-4 py-6">
        <h1 className="text-2xl font-bold mb-6">{t("anomaly.title")}</h1>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="bg-card rounded-lg p-4 border border-border">
            <p className="text-sm text-muted-foreground mb-1">{t("anomaly.totalFlags")}</p>
            <p className="text-2xl font-bold text-accent">{metrics.total_flags}</p>
          </div>
          <div className="bg-card rounded-lg p-4 border border-border">
            <p className="text-sm text-muted-foreground mb-1">{t("anomaly.avgPerExpense")}</p>
            <p className="text-2xl font-bold text-primary" dir="ltr">{metrics.avg_flags_per_expense.toFixed(2)}</p>
          </div>
          <div className="bg-card rounded-lg p-4 border border-border">
            <p className="text-sm text-muted-foreground mb-1">{t("anomaly.rejectionCorrelation")}</p>
            <p className="text-2xl font-bold text-destructive" dir="ltr">{(metrics.rejection_correlation * 100).toFixed(0)}%</p>
          </div>
        </div>

        <div className="bg-card rounded-lg p-4 border border-border">
          <h2 className="text-lg font-semibold mb-4">{t("anomaly.byType")}</h2>
          <div className="space-y-3">
            {TYPE_KEYS.map((type) => {
              const count = metrics.by_type[type] || 0;
              return (
                <div key={type} className="flex items-center justify-between">
                  <span className="text-card-foreground">{t(`anomaly.types.${type}`)}</span>
                  <div className="flex items-center gap-3">
                    <div
                      className="w-24 sm:w-32 bg-secondary rounded-full h-2"
                      role="progressbar"
                      aria-valuenow={count}
                      aria-valuemax={metrics.total_flags}
                      aria-label={t(`anomaly.types.${type}`)}
                    >
                      <div
                        className="bg-accent h-2 rounded-full transition-all"
                        style={{ width: `${metrics.total_flags > 0 ? (count / metrics.total_flags) * 100 : 0}%` }}
                      />
                    </div>
                    <span className="text-sm text-muted-foreground w-8 text-end" dir="ltr">{count}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <p className="text-xs text-muted-foreground mt-4">
          {t("anomaly.period", { days: metrics.period_days })}
        </p>
      </div>
    </div>
  );
}

import { useTranslation } from "react-i18next";
import { useAnalytics } from "../hooks/useAnalytics";
import DashboardSummary from "../components/DashboardSummary";
import SpendByProjectBar from "../components/SpendByProjectBar";
import SpendByCategoryDonut from "../components/SpendByCategoryDonut";
import SpendTrendLine from "../components/SpendTrendLine";
import BudgetVsActualBar from "../components/BudgetVsActualBar";
import ExportButton from "../components/ExportButton";

const PERIOD_OPTIONS = [
  { days: 7, key: "last7" },
  { days: 30, key: "last30" },
  { days: 90, key: "last90" },
  { days: 365, key: "last365" },
] as const;

export default function AnalyticsDashboard() {
  const { t } = useTranslation("analytics");
  const { spendByProject, spendByCategory, spendTrend, budgetVsActual, summary, loading, error, period, setPeriod } = useAnalytics();

  if (loading) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
        <p className="text-muted-foreground">{t("loading")}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center gap-2">
        <h2 className="text-xl font-semibold">{t("error.title")}</h2>
        <p className="text-destructive">{error}</p>
      </div>
    );
  }

  const hasData = (spendByProject?.length ?? 0) > 0 || (spendByCategory?.length ?? 0) > 0;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <h1 className="text-2xl font-bold">{t("title")}</h1>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <ExportButton period={period} />
            <div className="flex items-center gap-2 overflow-x-auto" role="group" aria-label={t("filters.period")}>
              {PERIOD_OPTIONS.map((opt) => (
                <button
                  key={opt.days}
                  onClick={() => setPeriod(opt.days as typeof period)}
                  className={`px-3 py-1.5 rounded text-sm transition-colors min-h-[44px] whitespace-nowrap ${
                    period === opt.days
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                  }`}
                  aria-pressed={period === opt.days}
                >
                  {t(`filters.${opt.key}`)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {summary && (
          <div className="mb-6">
            <DashboardSummary
              totalSpend={summary.total_spend}
              expenseCount={summary.expense_count}
              projectCount={summary.project_count}
            />
          </div>
        )}

        {!hasData && (
          <div className="text-center py-16">
            <h2 className="text-xl text-muted-foreground mb-2">{t("empty.title")}</h2>
            <p className="text-muted-foreground">{t("empty.description")}</p>
          </div>
        )}

        {hasData && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {spendByProject && spendByProject.length > 0 && (
                <SpendByProjectBar data={spendByProject} />
              )}
              {spendByCategory && spendByCategory.length > 0 && (
                <SpendByCategoryDonut data={spendByCategory} />
              )}
            </div>

            {spendTrend && spendTrend.length > 0 && (
              <SpendTrendLine data={spendTrend} />
            )}

            {budgetVsActual && budgetVsActual.length > 0 && (
              <BudgetVsActualBar data={budgetVsActual} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

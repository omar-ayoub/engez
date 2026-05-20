import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/lib/auth";
import { useAiMetrics } from "../hooks/useAiMetrics";

export default function AiMetricsPage() {
  const { t } = useTranslation("review");
  const user = useAuthStore((s) => s.user);
  const { data, loading, error } = useAiMetrics();

  if (user?.role !== "admin") {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <p className="text-gray-400">{t("metrics.accessDenied")}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <p className="text-gray-400">{t("metrics.loading")}</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <p className="text-red-400">{error || t("metrics.error")}</p>
      </div>
    );
  }

  const maxFieldCount = Math.max(...data.corrections_by_field.map((f) => f.count), 1);

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="max-w-5xl mx-auto px-4 py-6">
        <h1 className="text-2xl font-bold mb-6">{t("metrics.title")}</h1>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <MetricCard label={t("metrics.totalExpenses")} value={data.total_expenses} />
          <MetricCard label={t("metrics.totalAiExpenses")} value={data.total_ai_expenses} />
          <MetricCard label={t("metrics.totalCorrections")} value={data.total_corrections} />
          <MetricCard label={t("metrics.correctionRate")} value={`${(data.correction_rate * 100).toFixed(1)}%`} />
        </div>

        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-4">{t("metrics.byField")}</h2>
          <div className="space-y-2">
            {data.corrections_by_field.map((field) => (
              <div key={field.field_name} className="flex items-center gap-3">
                <span className="text-gray-400 text-sm w-32">
                  {t(`correct.field.${field.field_name}`)}
                </span>
                <div className="flex-1 bg-gray-800 rounded-full h-6 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      field.count === maxFieldCount ? "bg-red-600" : "bg-blue-600"
                    }`}
                    style={{ width: `${(field.count / maxFieldCount) * 100}%` }}
                  />
                </div>
                <span className="text-gray-400 text-sm w-20 text-end" dir="ltr">
                  {field.count} ({(field.rate * 100).toFixed(1)}%)
                </span>
              </div>
            ))}
          </div>
        </div>

        {data.daily_trend.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold mb-4">{t("metrics.dailyTrend")}</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-400 border-b border-gray-700">
                    <th className="text-start py-2 ps-3">{t("metrics.date")}</th>
                    <th className="text-start py-2 ps-3">{t("metrics.aiExpenses")}</th>
                    <th className="text-start py-2 ps-3">{t("metrics.corrections")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.daily_trend.map((row) => (
                    <tr key={row.date} className="border-b border-gray-800">
                      <td className="py-2 ps-3 text-gray-300" dir="ltr">{row.date}</td>
                      <td className="py-2 ps-3" dir="ltr">{row.ai_expenses}</td>
                      <td className="py-2 ps-3" dir="ltr">{row.corrections}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="p-4 bg-gray-800/50 rounded-lg">
      <p className="text-gray-400 text-xs mb-1">{label}</p>
      <p className="text-2xl font-bold" dir="ltr">{value}</p>
    </div>
  );
}

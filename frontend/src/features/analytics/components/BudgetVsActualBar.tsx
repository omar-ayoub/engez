import { useTranslation } from "react-i18next";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { chartTheme, chartTooltipStyle } from "../chartConfig";

interface Props {
  data: Array<{ name: string; name_ar: string; budget: number | null; actual_spend: number }>;
}

export default function BudgetVsActualBar({ data }: Props) {
  const { t, i18n } = useTranslation("analytics");
  if (!data.length) return null;

  const isAr = i18n.language === "ar";
  const chartData = data.map((d) => ({
    name: isAr ? d.name_ar : d.name,
    budget: d.budget || 0,
    actual: d.actual_spend,
  }));

  return (
    <div className="bg-card rounded-lg p-4 border border-border">
      <h3 className="text-lg font-semibold mb-4">{t("charts.budgetVsActual")}</h3>
      <div className="h-[200px] sm:h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
            <XAxis dataKey="name" tick={{ fill: chartTheme.tick, fontSize: 12 }} />
            <YAxis tick={{ fill: chartTheme.tick }} />
            <Tooltip
              {...chartTooltipStyle}
              formatter={(value: unknown, name: unknown) => [
                String(value),
                name === "budget" ? t("charts.budget") : t("charts.actual"),
              ]}
            />
            <Legend
              formatter={(value: string) => (
                <span style={{ color: chartTheme.legendText }}>
                  {value === "budget" ? t("charts.budget") : t("charts.actual")}
                </span>
              )}
            />
            <Bar dataKey="budget" fill="#60A5FA" radius={[4, 4, 0, 0]} />
            <Bar dataKey="actual" fill="#3B82F6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

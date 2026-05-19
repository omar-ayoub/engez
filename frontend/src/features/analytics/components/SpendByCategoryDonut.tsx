import { useTranslation } from "react-i18next";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { chartTheme, chartTooltipStyle } from "../chartConfig";

interface Props {
  data: Array<{ category: string; category_ar: string; total: number; count: number }>;
}

const COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16"];

export default function SpendByCategoryDonut({ data }: Props) {
  const { t, i18n } = useTranslation("analytics");
  if (!data.length) return null;

  const isAr = i18n.language === "ar";

  return (
    <div className="bg-card rounded-lg p-4 border border-border">
      <h3 className="text-lg font-semibold mb-4">{t("charts.spendByCategory")}</h3>
      <div className="h-[200px] sm:h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="total"
              nameKey={isAr ? "category_ar" : "category"}
              cx="50%"
              cy="50%"
              innerRadius="40%"
              outerRadius="65%"
              paddingAngle={2}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              {...chartTooltipStyle}
              formatter={(value: unknown) => [String(value), t("charts.spend")]}
            />
            <Legend
              formatter={(value: string) => <span style={{ color: chartTheme.legendText }}>{value}</span>}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

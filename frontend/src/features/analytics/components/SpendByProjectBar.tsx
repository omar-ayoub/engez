import { useTranslation } from "react-i18next";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from "recharts";
import { chartTheme, chartTooltipStyle } from "../chartConfig";

interface Props {
  data: Array<{ name: string; name_ar: string; budget: number | null; total_spend: number }>;
}

export default function SpendByProjectBar({ data }: Props) {
  const { t, i18n } = useTranslation("analytics");
  if (!data.length) return null;

  const isAr = i18n.language === "ar";

  return (
    <div className="bg-card rounded-lg p-4 border border-border">
      <h3 className="text-lg font-semibold mb-4">{t("charts.spendByProject")}</h3>
      <div className="h-[200px] sm:h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
            <XAxis type="number" tick={{ fill: chartTheme.tick }} />
            <YAxis
              type="category"
              dataKey={isAr ? "name_ar" : "name"}
              tick={{ fill: chartTheme.tick, fontSize: 12 }}
              width={60}
            />
            <Tooltip
              {...chartTooltipStyle}
              formatter={(value: unknown) => [String(value), t("charts.spend")]}
            />
            <Bar dataKey="total_spend" radius={[0, 4, 4, 0]}>
              {data.map((_, i) => (
                <Cell key={i} fill={i % 2 === 0 ? "#3B82F6" : "#60A5FA"} />
              ))}
            </Bar>
            {data.some((d) => d.budget) && (
              <ReferenceLine x={0} stroke="#EF4444" strokeDasharray="3 3" />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

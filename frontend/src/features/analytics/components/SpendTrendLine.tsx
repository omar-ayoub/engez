import { useTranslation } from "react-i18next";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { chartTheme, chartTooltipStyle } from "../chartConfig";

interface Props {
  data: Array<{ week: string; total: number; count: number }>;
}

export default function SpendTrendLine({ data }: Props) {
  const { t } = useTranslation("analytics");
  if (!data.length) return null;

  return (
    <div className="bg-card rounded-lg p-4 border border-border">
      <h3 className="text-lg font-semibold mb-4">{t("charts.spendTrend")}</h3>
      <div className="h-[200px] sm:h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <defs>
              <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
            <XAxis
              dataKey="week"
              tick={{ fill: chartTheme.tick, fontSize: 12 }}
              tickFormatter={(v: string) => v.slice(5)}
            />
            <YAxis tick={{ fill: chartTheme.tick }} />
            <Tooltip
              {...chartTooltipStyle}
              formatter={(value: unknown) => [String(value), t("charts.spend")]}
            />
            <Area
              type="monotone"
              dataKey="total"
              stroke="#3B82F6"
              strokeWidth={2}
              fill="url(#spendGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

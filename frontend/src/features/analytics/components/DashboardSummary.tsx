import { useTranslation } from "react-i18next";

interface SummaryProps {
  totalSpend: number;
  expenseCount: number;
  projectCount: number;
}

export default function DashboardSummary({ totalSpend, expenseCount, projectCount }: SummaryProps) {
  const { t, i18n } = useTranslation("analytics");
  const numLocale = i18n.language === "ar" ? "ar-EG" : "en-US";

  const cards = [
    { label: t("summary.totalSpend"), value: `${totalSpend.toLocaleString(numLocale)} ج.م`, color: "text-success" },
    { label: t("summary.expenseCount"), value: expenseCount.toLocaleString(numLocale), color: "text-primary" },
    { label: t("summary.projectCount"), value: projectCount.toLocaleString(numLocale), color: "text-purple-400" },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {cards.map((card) => (
        <div key={card.label} className="bg-card rounded-lg p-4 border border-border">
          <p className="text-sm text-muted-foreground mb-1">{card.label}</p>
          <p className={`text-2xl font-bold ${card.color}`} dir="ltr">
            {card.value}
          </p>
        </div>
      ))}
    </div>
  );
}

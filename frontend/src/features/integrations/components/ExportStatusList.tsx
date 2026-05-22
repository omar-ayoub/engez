import { useTranslation } from "react-i18next";

interface ExportItem {
  id: string;
  expense_id: string;
  system_name: string;
  status: string;
  external_ref_id: string | null;
  attempt_count: number;
  created_at: string;
}

interface Props {
  items: ExportItem[];
  onRetry: (expenseId: string) => void;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "text-yellow-400",
  success: "text-green-400",
  failed: "text-red-400",
  cancelled_migration: "text-muted-foreground",
};

export default function ExportStatusList({ items, onRetry }: Props) {
  const { t, i18n } = useTranslation("integrations");
  const dateLocale = i18n.language === "ar" ? "ar-EG" : "en-US";

  if (!items.length) {
    return (
      <div className="bg-card rounded-lg p-4 border border-border">
        <h3 className="text-lg font-semibold mb-3">{t("exports.title")}</h3>
        <p className="text-muted-foreground text-sm">{t("exports.noExports")}</p>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-lg p-4 border border-border">
      <h3 className="text-lg font-semibold mb-3">{t("exports.title")}</h3>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.id} className="flex items-center justify-between p-3 bg-background/50 rounded">
            <div className="flex items-center gap-3">
              <span className={`text-xs font-medium ${STATUS_COLORS[item.status] || "text-muted-foreground"}`}>
                {t(`exports.${item.status === "cancelled_migration" ? "cancelled" : item.status}`)}
              </span>
              <span className="text-sm text-muted-foreground" dir="ltr">
                {item.expense_id.slice(0, 8)}...
              </span>
              <span className="text-xs text-muted-foreground">
                {new Date(item.created_at).toLocaleDateString(dateLocale)}
              </span>
            </div>
            {item.status === "failed" && (
              <button
                onClick={() => onRetry(item.expense_id)}
                className="px-3 py-1 bg-secondary hover:bg-secondary/80 rounded text-xs min-h-[44px]"
              >
                {t("exports.retry")}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

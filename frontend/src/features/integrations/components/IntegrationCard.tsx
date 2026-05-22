import { useTranslation } from "react-i18next";

interface Props {
  systemName: string;
  displayName: string;
  status: string | null;
  lastSyncAt: string | null;
  onClick: () => void;
  active: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-900/30 text-green-400 border-green-700",
  pending: "bg-yellow-900/30 text-yellow-400 border-yellow-700",
  error: "bg-red-900/30 text-red-400 border-red-700",
  needs_reauth: "bg-orange-900/30 text-orange-400 border-orange-700",
};

export default function IntegrationCard({ displayName, status, lastSyncAt, onClick, active }: Props) {
  const { t, i18n } = useTranslation("integrations");
  const dateLocale = i18n.language === "ar" ? "ar-EG" : "en-US";

  return (
    <button
      onClick={onClick}
      className={`w-full text-start p-4 rounded-lg border transition-colors min-h-[44px] ${
        active ? "border-ring bg-primary/10" : "border-border bg-card hover:bg-secondary/50"
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium">{displayName}</span>
        {status && (
          <span className={`text-xs px-2 py-0.5 rounded border ${STATUS_COLORS[status] || STATUS_COLORS.pending}`}>
            {t(`status.${status}`)}
          </span>
        )}
      </div>
      {lastSyncAt && (
        <p className="text-xs text-muted-foreground">
          {t("status.lastSync")}: {new Date(lastSyncAt).toLocaleDateString(dateLocale)}
        </p>
      )}
    </button>
  );
}

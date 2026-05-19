import { useTranslation } from "react-i18next";

interface Props {
  status: string | null;
  lastError: string | null;
}

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-900/30 text-green-400 border-green-700",
  pending: "bg-yellow-900/30 text-yellow-400 border-yellow-700",
  error: "bg-red-900/30 text-red-400 border-red-700",
  needs_reauth: "bg-orange-900/30 text-orange-400 border-orange-700",
};

export default function ConnectionStatus({ status, lastError }: Props) {
  const { t } = useTranslation("integrations");

  if (!status) return null;

  return (
    <div className="bg-card rounded-lg p-4 border border-border">
      <div className="flex items-center gap-3">
        <span className={`text-sm px-3 py-1 rounded border ${STATUS_COLORS[status] || STATUS_COLORS.pending}`}>
          {t(`status.${status}`)}
        </span>
      </div>
      {lastError && (
        <p className="mt-2 text-sm text-destructive">
          {t("status.lastError")}: {lastError}
        </p>
      )}
    </div>
  );
}

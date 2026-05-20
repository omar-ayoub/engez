import { useTranslation } from "react-i18next";

interface ConfidenceBadgeProps {
  confidence: { min: number; all_high: boolean; low_count: number } | null | undefined;
}

export default function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const { t } = useTranslation("review");

  if (!confidence) return null;

  const level = confidence.all_high ? "high" : confidence.low_count === 0 ? "medium" : "low";
  const colors = {
    high: "bg-green-900/30 text-green-400 border-green-700",
    medium: "bg-yellow-900/30 text-yellow-400 border-yellow-700",
    low: "bg-red-900/30 text-red-400 border-red-700",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border ${colors[level]}`}
      role="status"
      aria-label={t(`confidence.${level}`)}
    >
      <span aria-hidden="true">
        {level === "high" ? "●" : level === "medium" ? "◐" : "○"}
      </span>
      {t(`confidence.${level}`)}
    </span>
  );
}

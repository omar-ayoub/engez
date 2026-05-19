import { useTranslation } from "react-i18next";

interface AnomalyFlag {
  severity: string;
  message: string;
  message_en: string;
  [key: string]: unknown;
}

interface AnomalyBadgesProps {
  flags: Record<string, AnomalyFlag> | null;
}

export default function AnomalyBadges({ flags }: AnomalyBadgesProps) {
  const { i18n } = useTranslation();
  if (!flags || Object.keys(flags).length === 0) return null;

  const severityColors: Record<string, string> = {
    high: "bg-red-900/30 text-red-400 border-red-700",
    medium: "bg-yellow-900/30 text-yellow-400 border-yellow-700",
    low: "bg-blue-900/30 text-blue-400 border-blue-700",
  };

  return (
    <div className="flex flex-wrap gap-2">
      {Object.entries(flags).map(([type, flag]) => (
        <span
          key={type}
          className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs border ${
            severityColors[flag.severity] || severityColors.low
          }`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-current" />
          {i18n.language === "ar" ? flag.message : flag.message_en}
        </span>
      ))}
    </div>
  );
}

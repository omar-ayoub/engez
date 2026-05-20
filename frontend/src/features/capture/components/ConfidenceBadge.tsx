import { useTranslation } from "react-i18next";

interface ConfidenceBadgeProps {
  score: number;
}

export default function ConfidenceBadge({ score }: ConfidenceBadgeProps) {
  const { t } = useTranslation("capture");

  let color: string;
  if (score >= 0.8) {
    color = "bg-success";
  } else if (score >= 0.5) {
    color = "bg-accent";
  } else {
    color = "bg-danger";
  }

  return (
    <span
      className={`inline-block size-2 rounded-full ${color}`}
      role="status"
      aria-label={t("confidence.label", { score: Math.round(score * 100) })}
    />
  );
}

import { useTranslation } from "react-i18next";
import { useDraftProcessor } from "../hooks/useDraftProcessor";
import { Bell } from "lucide-react";

interface DraftReviewBannerProps {
  onReview: () => void;
}

export default function DraftReviewBanner({ onReview }: DraftReviewBannerProps) {
  const { t } = useTranslation("capture");
  const { unprocessedCount, processedDrafts } = useDraftProcessor();

  const readyCount = processedDrafts.length;

  if (readyCount === 0 && unprocessedCount === 0) return null;

  return (
    <button
      type="button"
      onClick={onReview}
      className="flex w-full items-center gap-3 rounded-xl bg-brand/10 px-4 py-3 text-start transition-colors active:bg-brand/20"
    >
      <Bell className="size-5 shrink-0 text-brand" />
      <div className="flex-1">
        {readyCount > 0 && (
          <p className="text-sm font-medium text-foreground">
            {t("sync.draftsReady", { count: readyCount })}
          </p>
        )}
        {unprocessedCount > 0 && (
          <p className="text-xs text-muted-foreground">
            {t("sync.draftsUnprocessed", { count: unprocessedCount })}
          </p>
        )}
      </div>
      <span className="shrink-0 text-xs text-brand">{t("sync.reviewDrafts")}</span>
    </button>
  );
}

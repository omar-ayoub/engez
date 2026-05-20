import { useState } from "react";
import { useTranslation } from "react-i18next";
import { bulkApprove } from "../review-api";
import { addReviewAction, removeReviewAction } from "@/lib/review-sync";
import { useAuthStore } from "@/lib/auth";
import type { ReviewQueueItem } from "../review-types";

interface BulkActionBarProps {
  selectedIds: Set<string>;
  items: ReviewQueueItem[];
  onClear: () => void;
  onComplete: () => void;
}

export default function BulkActionBar({ selectedIds, items, onClear, onComplete }: BulkActionBarProps) {
  const { t } = useTranslation("review");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    approved: number;
    skipped: number;
    conflicts: number;
  } | null>(null);

  const handleBulkApprove = async () => {
    if (selectedIds.size === 0) return;
    setLoading(true);
    setResult(null);

    const companyId = useAuthStore.getState().user?.company_id || "unknown";
    const bulkItems = items
      .filter((item) => selectedIds.has(item.id))
      .map((item) => ({ id: item.id, review_version: item.review_version }));

    const outboxItem = await addReviewAction(
      companyId,
      "bulk_approve",
      { items: bulkItems },
    );

    try {
      const response = await bulkApprove({ items: bulkItems });
      await removeReviewAction(outboxItem.id);
      setResult({
        approved: response.approved,
        skipped: response.skipped.length,
        conflicts: response.conflicts.length,
      });
      setTimeout(() => {
        onComplete();
      }, 2000);
    } catch {
      onComplete();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-0 inset-x-0 bg-gray-800 border-t border-gray-700 px-4 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-white font-medium">
            {t("bulk.selected", { count: selectedIds.size })}
          </span>
          <button
            onClick={onClear}
            className="text-gray-400 hover:text-white text-sm min-h-[44px] px-3"
          >
            {t("list.deselectAll")}
          </button>
        </div>

        <div className="flex items-center gap-4">
          {result && (
            <div className="flex gap-3 text-sm">
              <span className="text-green-400">{t("bulk.approved", { count: result.approved })}</span>
              {result.skipped > 0 && (
                <span className="text-yellow-400">{t("bulk.skipped", { count: result.skipped })}</span>
              )}
              {result.conflicts > 0 && (
                <span className="text-red-400">{t("bulk.conflicts", { count: result.conflicts })}</span>
              )}
            </div>
          )}
          <button
            onClick={handleBulkApprove}
            disabled={selectedIds.size === 0 || loading}
            className="px-6 py-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded font-medium transition-colors min-h-[44px]"
          >
            {loading
              ? t("actions.pendingConfirmation")
              : selectedIds.size > 0
                ? t("actions.bulkApprove", { count: selectedIds.size })
                : t("actions.bulkApproveZero")}
          </button>
        </div>
      </div>
    </div>
  );
}

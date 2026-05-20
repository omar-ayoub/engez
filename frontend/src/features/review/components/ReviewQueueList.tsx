import { useTranslation } from "react-i18next";
import type { ReviewQueueItem } from "../review-types";

interface ReviewQueueListProps {
  items: ReviewQueueItem[];
  totalCount: number;
  page: number;
  pageSize: number;
  pages: number;
  selectedIds: Set<string>;
  selectionMode: boolean;
  onToggleSelect: (id: string) => void;
  onNavigateToDetail: (expenseId: string) => void;
  onPageChange: (page: number) => void;
  hasActiveFilters?: boolean;
}

export default function ReviewQueueList({
  items,
  page,
  pages,
  selectedIds,
  selectionMode,
  onToggleSelect,
  onNavigateToDetail,
  onPageChange,
  hasActiveFilters = false,
}: ReviewQueueListProps) {
  const { t } = useTranslation("review");

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <p className="text-lg">
          {hasActiveFilters ? t("queue.emptyFiltered") : t("queue.noPendingTitle")}
        </p>
        <p className="text-sm mt-1">
          {hasActiveFilters ? "" : t("queue.noPendingDesc")}
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-start text-gray-400 border-b border-gray-700">
              {selectionMode && <th className="ps-3 py-3 w-10"></th>}
              <th className="ps-3 py-3 text-start">{t("list.amount")}</th>
              <th className="ps-3 py-3 text-start">{t("list.vendor")}</th>
              <th className="ps-3 py-3 text-start">{t("list.employee")}</th>
              <th className="ps-3 py-3 text-start">{t("list.project")}</th>
              <th className="ps-3 py-3 text-start">{t("list.captureMode")}</th>
              <th className="ps-3 py-3 text-start">{t("list.date")}</th>
              <th className="ps-3 py-3 text-start">{t("list.confidence")}</th>
              <th className="ps-3 py-3 text-start">{t("list.etaVerified")}</th>
              <th className="ps-3 py-3 text-start">{t("list.anomaly")}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const isSelected = selectedIds.has(item.id);
              const isDisabled = selectionMode && !item.bulk_eligible;

              return (
                <tr
                  key={item.id}
                  className={`border-b border-gray-700/50 hover:bg-gray-700/30 cursor-pointer transition-colors ${
                    isDisabled ? "opacity-50" : ""
                  } ${isSelected ? "bg-blue-900/20" : ""}`}
                  onClick={() => {
                    if (selectionMode) {
                      if (item.bulk_eligible) onToggleSelect(item.id);
                    } else {
                      onNavigateToDetail(item.id);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  aria-label={`${item.vendor || "Expense"} ${item.amount} ${item.currency}`}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      if (selectionMode && item.bulk_eligible) onToggleSelect(item.id);
                      else if (!selectionMode) onNavigateToDetail(item.id);
                    }
                  }}
                >
                  {selectionMode && (
                    <td className="ps-3 py-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        disabled={isDisabled}
                        onChange={() => item.bulk_eligible && onToggleSelect(item.id)}
                        className="w-5 h-5 rounded"
                        aria-label={`Select expense ${item.id}`}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </td>
                  )}
                  <td className="ps-3 py-3 font-mono" dir="ltr">
                    {item.amount.toLocaleString("en", { minimumFractionDigits: 2 })} {item.currency}
                  </td>
                  <td className="ps-3 py-3">{item.vendor || "—"}</td>
                  <td className="ps-3 py-3">{item.employee.name_ar}</td>
                  <td className="ps-3 py-3">{item.project?.name_ar || "—"}</td>
                  <td className="ps-3 py-3">{t(`captureMode.${item.capture_mode}`)}</td>
                  <td className="ps-3 py-3 text-gray-400">
                    {new Date(item.created_at).toLocaleDateString("ar-EG")}
                  </td>
                  <td className="ps-3 py-3">
                    <ConfidenceLabel confidence={item.confidence_summary} />
                  </td>
                  <td className="ps-3 py-3">
                    {item.eta_verified ? (
                      <span className="text-green-400 text-xs" aria-label={t("list.etaVerified")}>✓ ETA</span>
                    ) : null}
                  </td>
                  <td className="ps-3 py-3">
                    {item.anomaly_count > 0 ? (
                      <span className="text-yellow-400 text-xs" aria-label={`${item.anomaly_count} ${t("list.anomalies")}`}>
                        {item.anomaly_count} {t("list.anomalies")}
                      </span>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {pages > 1 && (
        <div className="flex items-center justify-center gap-3 py-4">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="px-4 py-2 bg-gray-700 rounded disabled:opacity-50 hover:bg-gray-600 transition-colors min-h-[44px]"
            aria-label={t("list.prev")}
          >
            {t("list.prev")}
          </button>
          <span className="text-gray-400 text-sm" aria-label={t("list.page", { current: page, total: pages })}>
            {t("list.page", { current: page, total: pages })}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= pages}
            className="px-4 py-2 bg-gray-700 rounded disabled:opacity-50 hover:bg-gray-600 transition-colors min-h-[44px]"
            aria-label={t("list.next")}
          >
            {t("list.next")}
          </button>
        </div>
      )}
    </div>
  );
}

function ConfidenceLabel({ confidence }: { confidence: ReviewQueueItem["confidence_summary"] }) {
  const { t } = useTranslation("review");

  if (!confidence) return <span className="text-gray-500">—</span>;

  const level = confidence.all_high ? "high" : confidence.low_count === 0 ? "medium" : "low";
  const colors = { high: "text-green-400", medium: "text-yellow-400", low: "text-red-400" };

  return (
    <span className={`${colors[level]} text-xs`} aria-label={t(`confidence.${level}`)}>
      {t(`confidence.${level}`)}
    </span>
  );
}

import { useState, useCallback } from "react";
import { useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { useReviewQueue } from "../hooks/useReviewQueue";
import ReviewFilters from "../components/ReviewFilters";
import ReviewQueueList from "../components/ReviewQueueList";
import BulkActionBar from "../components/BulkActionBar";

export default function ReviewQueuePage() {
  const { t } = useTranslation("review");
  const navigate = useNavigate();
  const { data, loading, error, isOffline, filters, updateFilters, refresh, pendingCount, conflictCount } = useReviewQueue();
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleSelectionMode = useCallback(() => {
    setSelectionMode((prev) => {
      if (prev) setSelectedIds(new Set());
      return !prev;
    });
  }, []);

  if (loading && !data) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <p className="text-gray-400">{t("queue.loading")}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">{t("queue.title")}</h1>
          <div className="flex items-center gap-3">
            {isOffline && (
              <span className="text-yellow-400 text-sm px-3 py-1 bg-yellow-900/20 rounded">
                {t("offline.title")}
              </span>
            )}
            {pendingCount > 0 && (
              <span className="text-blue-400 text-sm px-3 py-1 bg-blue-900/20 rounded">
                {t("offline.pendingActions", { count: pendingCount })}
              </span>
            )}
            {conflictCount > 0 && (
              <span className="text-red-400 text-sm px-3 py-1 bg-red-900/20 rounded">
                {t("offline.conflictActions", { count: conflictCount })}
              </span>
            )}
            <button
              onClick={refresh}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded transition-colors text-sm min-h-[44px]"
              aria-label={t("queue.refresh")}
            >
              {t("queue.refresh")}
            </button>
            <button
              onClick={toggleSelectionMode}
              className={`px-4 py-2 rounded transition-colors text-sm min-h-[44px] ${
                selectionMode ? "bg-blue-600 hover:bg-blue-500" : "bg-gray-700 hover:bg-gray-600"
              }`}
            >
              {selectionMode ? t("list.deselectAll") : t("list.selectionMode")}
            </button>
          </div>
        </div>

        <ReviewFilters filters={filters} onUpdate={updateFilters} />

        {error && !data && (
          <div className="text-center py-16 text-red-400">
            <p>{error}</p>
            <button onClick={refresh} className="mt-3 px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 min-h-[44px]">
              {t("queue.refresh")}
            </button>
          </div>
        )}

        {data && (
          <>
            <ReviewQueueList
              items={data.items}
              totalCount={data.total}
              page={data.page}
              pageSize={data.page_size}
              pages={data.pages}
              selectedIds={selectedIds}
              selectionMode={selectionMode}
              onToggleSelect={toggleSelect}
              onNavigateToDetail={(id) => navigate(`/review/${id}`)}
              onPageChange={(p) => updateFilters({ page: p })}
              hasActiveFilters={
                (filters.status && filters.status !== "pending") ||
                !!filters.project_id ||
                !!filters.employee_id ||
                !!filters.date_from ||
                !!filters.date_to ||
                filters.amount_min !== undefined ||
                filters.amount_max !== undefined
              }
            />

            {selectionMode && (
              <BulkActionBar
                selectedIds={selectedIds}
                items={data.items}
                onClear={() => setSelectedIds(new Set())}
                onComplete={() => {
                  setSelectedIds(new Set());
                  refresh();
                }}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}

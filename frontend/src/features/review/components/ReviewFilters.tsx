import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/lib/auth";
import { db } from "@/lib/db";
import { useState, useEffect } from "react";
import type { ReviewQueueFilters } from "../review-types";

interface ReviewFiltersProps {
  filters: ReviewQueueFilters;
  onUpdate: (updates: Partial<ReviewQueueFilters>) => void;
}

interface FilterOption {
  id: string;
  label: string;
}

export default function ReviewFilters({ filters, onUpdate }: ReviewFiltersProps) {
  const { t } = useTranslation("review");
  const companyId = useAuthStore.getState().user?.company_id || "";
  const [projects, setProjects] = useState<FilterOption[]>([]);

  useEffect(() => {
    async function loadFilterOptions() {
      try {
        const projs = await db.projects
          .where("companyId")
          .equals(companyId)
          .toArray();
        setProjects(projs.map((p) => ({ id: p.id, label: p.nameAr || p.name })));
      } catch {
        setProjects([]);
      }
    }
    if (companyId) loadFilterOptions();
  }, [companyId]);

  return (
    <div className="flex flex-wrap gap-3 items-end p-4 bg-gray-800/50 rounded-lg">
      <div className="min-w-[140px]">
        <label className="block text-xs text-gray-400 mb-1">{t("filters.status")}</label>
        <select
          value={filters.status || "pending"}
          onChange={(e) => onUpdate({ status: e.target.value, page: 1 })}
          className="w-full bg-gray-700 text-white rounded px-3 py-2 text-sm border border-gray-600 focus:border-blue-500 focus:outline-none"
          aria-label={t("filters.status")}
        >
          <option value="pending">{t("filters.pending")}</option>
          <option value="approved">{t("filters.approved")}</option>
          <option value="rejected">{t("filters.rejected")}</option>
          <option value="all">{t("filters.allStatuses")}</option>
        </select>
      </div>

      {projects.length > 0 && (
        <div className="min-w-[140px]">
          <label className="block text-xs text-gray-400 mb-1">{t("filters.project")}</label>
          <select
            value={filters.project_id || ""}
            onChange={(e) => onUpdate({ project_id: e.target.value || undefined, page: 1 })}
            className="w-full bg-gray-700 text-white rounded px-3 py-2 text-sm border border-gray-600 focus:border-blue-500 focus:outline-none"
            aria-label={t("filters.project")}
          >
            <option value="">{t("filters.allProjects")}</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </select>
        </div>
      )}

      <div className="min-w-[140px]">
        <label className="block text-xs text-gray-400 mb-1">{t("filters.employee")}</label>
        <input
          type="text"
          placeholder={t("filters.allEmployees")}
          value={filters.employee_id || ""}
          onChange={(e) => onUpdate({ employee_id: e.target.value || undefined, page: 1 })}
          className="w-full bg-gray-700 text-white rounded px-3 py-2 text-sm border border-gray-600 focus:border-blue-500 focus:outline-none"
          aria-label={t("filters.employee")}
        />
      </div>

      <div className="min-w-[140px]">
        <label className="block text-xs text-gray-400 mb-1">{t("filters.sortBy")}</label>
        <select
          value={filters.sort_by || "date"}
          onChange={(e) => onUpdate({ sort_by: e.target.value as ReviewQueueFilters["sort_by"], page: 1 })}
          className="w-full bg-gray-700 text-white rounded px-3 py-2 text-sm border border-gray-600 focus:border-blue-500 focus:outline-none"
          aria-label={t("filters.sortBy")}
        >
          <option value="date">{t("filters.sortDate")}</option>
          <option value="amount">{t("filters.sortAmount")}</option>
          <option value="project">{t("filters.sortProject")}</option>
        </select>
      </div>

      <div className="min-w-[120px]">
        <label className="block text-xs text-gray-400 mb-1">{t("filters.sortOrder")}</label>
        <select
          value={filters.sort_order || "desc"}
          onChange={(e) => onUpdate({ sort_order: e.target.value as ReviewQueueFilters["sort_order"], page: 1 })}
          className="w-full bg-gray-700 text-white rounded px-3 py-2 text-sm border border-gray-600 focus:border-blue-500 focus:outline-none"
          aria-label={t("filters.sortOrder")}
        >
          <option value="desc">{t("filters.sortDesc")}</option>
          <option value="asc">{t("filters.sortAsc")}</option>
        </select>
      </div>

      <div className="min-w-[120px]">
        <label className="block text-xs text-gray-400 mb-1">{t("filters.amountRange")}</label>
        <div className="flex gap-1">
          <input
            type="number"
            placeholder={t("filters.min")}
            value={filters.amount_min ?? ""}
            onChange={(e) => onUpdate({ amount_min: e.target.value ? Number(e.target.value) : undefined, page: 1 })}
            className="w-full bg-gray-700 text-white rounded px-2 py-2 text-sm border border-gray-600 focus:border-blue-500 focus:outline-none min-h-[44px]"
            min={0}
            aria-label={t("filters.min")}
          />
          <input
            type="number"
            placeholder={t("filters.max")}
            value={filters.amount_max ?? ""}
            onChange={(e) => onUpdate({ amount_max: e.target.value ? Number(e.target.value) : undefined, page: 1 })}
            className="w-full bg-gray-700 text-white rounded px-2 py-2 text-sm border border-gray-600 focus:border-blue-500 focus:outline-none min-h-[44px]"
            min={0}
            aria-label={t("filters.max")}
          />
        </div>
      </div>

      <div className="min-w-[140px]">
        <label className="block text-xs text-gray-400 mb-1">{t("filters.dateRange")}</label>
        <div className="flex gap-1">
          <input
            type="date"
            value={filters.date_from || ""}
            onChange={(e) => onUpdate({ date_from: e.target.value || undefined, page: 1 })}
            className="w-full bg-gray-700 text-white rounded px-2 py-2 text-sm border border-gray-600 focus:border-blue-500 focus:outline-none min-h-[44px]"
            aria-label={t("filters.from")}
          />
          <input
            type="date"
            value={filters.date_to || ""}
            onChange={(e) => onUpdate({ date_to: e.target.value || undefined, page: 1 })}
            className="w-full bg-gray-700 text-white rounded px-2 py-2 text-sm border border-gray-600 focus:border-blue-500 focus:outline-none min-h-[44px]"
            aria-label={t("filters.to")}
          />
        </div>
      </div>

      <button
        onClick={() =>
          onUpdate({
            status: "pending",
            project_id: undefined,
            employee_id: undefined,
            date_from: undefined,
            date_to: undefined,
            amount_min: undefined,
            amount_max: undefined,
            sort_by: "date",
            sort_order: "desc",
            page: 1,
          })
        }
        className="px-4 py-2 text-sm text-gray-300 hover:text-white bg-gray-700 hover:bg-gray-600 rounded transition-colors min-h-[44px]"
      >
        {t("filters.clear")}
      </button>
    </div>
  );
}

import { useTranslation } from "react-i18next";
import type { AuditHistoryItem } from "../review-types";

interface AuditTimelineProps {
  items: AuditHistoryItem[];
}

export default function AuditTimeline({ items }: AuditTimelineProps) {
  const { t } = useTranslation("review");

  if (items.length === 0) {
    return <p className="text-gray-500 text-sm">{t("detail.noAuditHistory")}</p>;
  }

  return (
    <div className="space-y-0">
      {items.map((item, idx) => (
        <div key={item.id} className="relative flex gap-3 pb-4">
          {idx < items.length - 1 && (
            <div className="absolute start-[15px] top-8 bottom-0 w-px bg-gray-700" />
          )}
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-xs text-gray-300">
            {item.action_type === "approve" && "✓"}
            {item.action_type === "reject" && "✗"}
            {item.action_type === "correct" && "✎"}
            {item.action_type === "bulk_approve" && "✓✓"}
            {item.action_type === "resubmit" && "↻"}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-white text-sm font-medium">
                {t(`audit.${item.action_type}`)}
              </span>
              <span className="text-gray-500 text-xs" dir="ltr">
                {new Date(item.created_at).toLocaleString("ar-EG")}
              </span>
            </div>
            {item.field_name && (
              <p className="text-gray-400 text-xs mt-0.5">
                {t("audit.fieldChanged", { field: t(`correct.field.${item.field_name}`) || item.field_name })}
              </p>
            )}
            {item.rejection_reason && (
              <p className="text-gray-400 text-xs mt-0.5">
                {t("audit.reason", { reason: item.rejection_reason })}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

import { useState } from "react";
import { useTranslation } from "react-i18next";
import InlineFieldEditor from "./InlineFieldEditor";
import type { ReviewDetailResponse } from "../review-types";

interface ExpenseEvidencePanelProps {
  detail: ReviewDetailResponse;
  onCorrect: (fieldName: string, correctedValue: string | number) => Promise<unknown>;
  correcting: boolean;
}

const EDITABLE_FIELDS = ["amount", "vendor", "vendor_tax_reg", "items", "category_id", "project_id", "notes"] as const;

export default function ExpenseEvidencePanel({
  detail,
  onCorrect,
  correcting,
}: ExpenseEvidencePanelProps) {
  const { t } = useTranslation("review");
  const [editingField, setEditingField] = useState<string | null>(null);

  const handleSave = async (fieldName: string, value: string | number) => {
    await onCorrect(fieldName, value);
    setEditingField(null);
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">
        {detail.capture_mode === "manual" ? t("detail.manualEntry") : t("detail.aiFields")}
      </h3>

      <div className="grid gap-3">
        {EDITABLE_FIELDS.map((field) => {
          const value = (detail as unknown as Record<string, unknown>)[field];
          const confidence = detail.ai_confidence?.[field];
          const isEditing = editingField === field;

          return (
            <div key={field} className="flex items-start gap-3 p-3 bg-gray-800/50 rounded">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-gray-400 text-sm">{t(`correct.field.${field}`)}</span>
                  {confidence !== undefined && (
                    <ConfidenceBadge value={confidence} />
                  )}
                </div>
                {isEditing ? (
                  <InlineFieldEditor
                    fieldName={field}
                    value={value}
                    onSave={(v) => handleSave(field, v)}
                    onCancel={() => setEditingField(null)}
                    loading={correcting}
                  />
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="text-white truncate">
                      {value !== null && value !== undefined ? String(value) : "—"}
                    </span>
                    {detail.status === "pending" && (
                      <button
                        onClick={() => setEditingField(field)}
                        className="text-blue-400 hover:text-blue-300 text-xs px-2 py-1 rounded min-h-[44px] min-w-[44px] flex items-center justify-center"
                        aria-label={t("actions.correct")}
                      >
                        {t("actions.correct")}
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {detail.voice_transcript && (
        <div className="p-3 bg-gray-800/50 rounded">
          <h4 className="text-gray-400 text-sm mb-1">{t("detail.transcript")}</h4>
          <p className="text-white whitespace-pre-wrap">{detail.voice_transcript}</p>
        </div>
      )}

      {detail.eta && detail.eta.verified && (
        <div className="p-3 bg-gray-800/50 rounded">
          <div className="flex items-center gap-2">
            <span className="text-green-400">✓</span>
            <span className="text-white text-sm">{t("detail.etaVerified")}</span>
            {detail.eta.uuid && (
              <span className="text-gray-400 text-xs" dir="ltr">
                {t("detail.etaUuid", { uuid: detail.eta.uuid })}
              </span>
            )}
          </div>
        </div>
      )}

      {detail.anomaly_flags && Object.entries(detail.anomaly_flags).filter(([, val]) => val).length > 0 && (
        <div className="p-3 bg-gray-800/50 rounded">
          <h4 className="text-gray-400 text-sm mb-2">{t("detail.anomalies")}</h4>
          <div className="flex flex-wrap gap-2">
            {Object.entries(detail.anomaly_flags).filter(([, val]) => val).map(([key]) => (
              <span key={key} className="px-2 py-1 bg-yellow-900/30 text-yellow-400 rounded text-xs">
                {t(`anomaly.${key}`)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ConfidenceBadge({ value }: { value: number }) {
  const { t } = useTranslation("review");
  const level = value >= 0.8 ? "high" : value >= 0.5 ? "medium" : "low";
  const colors = { high: "bg-green-900/30 text-green-400", medium: "bg-yellow-900/30 text-yellow-400", low: "bg-red-900/30 text-red-400" };

  return (
    <span className={`px-2 py-0.5 rounded text-xs ${colors[level]}`} aria-label={t(`confidence.${level}`)}>
      {Math.round(value * 100)}%
    </span>
  );
}

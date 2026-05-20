import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";

interface RejectReasonDialogProps {
  open: boolean;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
  loading: boolean;
}

export default function RejectReasonDialog({ open, onConfirm, onCancel, loading }: RejectReasonDialogProps) {
  const { t } = useTranslation("review");
  const [reason, setReason] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const trimmed = reason.trim();
  const isValid = trimmed.length >= 5;

  useEffect(() => {
    if (open) {
      setReason("");
      setTimeout(() => textareaRef.current?.focus(), 100);
    }
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-label={t("reject.title")}
    >
      <div
        className="bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-white mb-4">{t("reject.title")}</h2>
        <textarea
          ref={textareaRef}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder={t("reject.placeholder")}
          className="w-full bg-gray-700 text-white rounded p-3 text-sm border border-gray-600 focus:border-blue-500 focus:outline-none resize-none"
          rows={3}
          maxLength={1000}
          aria-label={t("reject.title")}
        />
        {!isValid && reason.length > 0 && (
          <p className="text-red-400 text-xs mt-1">{t("reject.minLength")}</p>
        )}
        <div className="flex justify-end gap-3 mt-4">
          <button
            onClick={onCancel}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded transition-colors text-sm min-h-[44px]"
          >
            {t("reject.cancel")}
          </button>
          <button
            onClick={() => onConfirm(trimmed)}
            disabled={!isValid || loading}
            className="px-4 py-2 bg-red-600 hover:bg-red-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors text-sm min-h-[44px]"
          >
            {t("reject.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}

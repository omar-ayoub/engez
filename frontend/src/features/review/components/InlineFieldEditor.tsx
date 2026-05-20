import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";

interface InlineFieldEditorProps {
  fieldName: string;
  value: unknown;
  onSave: (value: string | number) => Promise<void>;
  onCancel: () => void;
  loading: boolean;
}

export default function InlineFieldEditor({
  fieldName,
  value,
  onSave,
  onCancel,
  loading,
}: InlineFieldEditorProps) {
  const { t } = useTranslation("review");
  const inputRef = useRef<HTMLInputElement>(null);
  const isNumeric = fieldName === "amount";
  const [editValue, setEditValue] = useState(String(value ?? ""));

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  const handleSave = async () => {
    const saveValue = isNumeric ? Number(editValue) : editValue;
    if (isNumeric && isNaN(saveValue as number)) return;
    await onSave(saveValue);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSave();
    if (e.key === "Escape") onCancel();
  };

  return (
    <div className="flex items-center gap-2">
      <input
        ref={inputRef}
        type={isNumeric ? "number" : "text"}
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onKeyDown={handleKeyDown}
        className="flex-1 bg-gray-700 text-white rounded px-2 py-1 text-sm border border-blue-500 focus:outline-none"
        dir={isNumeric ? "ltr" : undefined}
        aria-label={t("correct.title", { field: t(`correct.field.${fieldName}`) })}
      />
      <button
        onClick={handleSave}
        disabled={loading}
        className="px-3 py-1 bg-green-600 hover:bg-green-500 disabled:bg-gray-600 rounded text-sm min-h-[44px]"
      >
        {loading ? t("correct.saving") : t("correct.save")}
      </button>
      <button
        onClick={onCancel}
        className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm min-h-[44px]"
      >
        {t("correct.cancel")}
      </button>
    </div>
  );
}

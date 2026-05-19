import { useState } from "react";
import { useTranslation } from "react-i18next";

interface Props {
  systemName: string;
  requiredFields: string[];
  onSave: (credentials: Record<string, string>) => void;
  onTest: (credentials: Record<string, string>) => void;
  testing: boolean;
  testResult: { success: boolean; message: string } | null;
}

export default function ConfigForm({ requiredFields, onSave, onTest, testing, testResult }: Props) {
  const { t } = useTranslation("integrations");
  const [credentials, setCredentials] = useState<Record<string, string>>(
    Object.fromEntries(requiredFields.map((f) => [f, ""])),
  );

  const update = (key: string, value: string) => {
    setCredentials((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(credentials);
  };

  const fieldLabel = (field: string) => t(`configure.fields.${field}`, { defaultValue: field });

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h3 className="text-lg font-semibold">{t("configure.title")}</h3>

      <div className="space-y-3">
        {requiredFields.map((field) => (
          <div key={field}>
            <label htmlFor={`field-${field}`} className="block text-sm text-muted-foreground mb-1">
              {fieldLabel(field)}
            </label>
            <input
              id={`field-${field}`}
              type={field.includes("password") || field.includes("token") || field.includes("secret") ? "password" : "text"}
              value={credentials[field] || ""}
              onChange={(e) => update(field, e.target.value)}
              className="w-full px-3 py-2 bg-card border border-input rounded text-foreground focus:border-ring focus:outline-none"
              dir="ltr"
            />
          </div>
        ))}
      </div>

      {testResult && (
        <div className={`p-3 rounded text-sm ${testResult.success ? "bg-green-900/20 text-green-400" : "bg-red-900/20 text-red-400"}`}>
          {testResult.message}
        </div>
      )}

      <div className="flex gap-3">
        <button
          type="button"
          onClick={() => onTest(credentials)}
          disabled={testing}
          className="px-4 py-2 bg-secondary hover:bg-secondary/80 rounded transition-colors min-h-[44px] disabled:opacity-50"
        >
          {testing ? t("configure.testing") : t("configure.testConnection")}
        </button>
        <button
          type="submit"
          className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded transition-colors min-h-[44px]"
        >
          {t("configure.save")}
        </button>
      </div>
    </form>
  );
}

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { getAvailable, getStatus, configure, testConnection, getExports, retryExport } from "../api";
import IntegrationCard from "../components/IntegrationCard";
import ConfigForm from "../components/ConfigForm";
import ConnectionStatus from "../components/ConnectionStatus";
import ExportStatusList from "../components/ExportStatusList";

export default function IntegrationSettings() {
  const { t } = useTranslation("integrations");

  const [systems, setSystems] = useState<Array<{ system_name: string; display_name: string; display_name_ar: string; required_fields: string[] }>>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [status, setStatus] = useState<{ configured: boolean; system_name?: string; status?: string; last_sync_at?: string; last_error?: string } | null>(null);
  const [exports, setExports] = useState<Array<{ id: string; expense_id: string; system_name: string; status: string; external_ref_id: string | null; attempt_count: number; created_at: string }>>([]);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getAvailable(), getStatus()])
      .then(([sys, st]) => {
        setSystems(sys);
        setStatus(st);
        if (st.configured && st.system_name) setSelected(st.system_name);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    getExports()
      .then((res) => setExports(res.items))
      .catch((err) => console.error("Failed to load exports:", err));
  }, []);

  const handleSave = useCallback(async (credentials: Record<string, string>) => {
    if (!selected) return;
    setActionError(null);
    try {
      await configure({ system_name: selected, credentials });
      const st = await getStatus();
      setStatus(st);
      setTestResult(null);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : t("configure.saveFailed"));
    }
  }, [selected, t]);

  const handleTest = useCallback(async (credentials: Record<string, string>) => {
    if (!selected) return;
    setTesting(true);
    setTestResult(null);
    setActionError(null);
    try {
      const result = await testConnection({ system_name: selected, credentials });
      setTestResult(result);
    } catch {
      setTestResult({ success: false, message: t("configure.failed") });
    } finally {
      setTesting(false);
    }
  }, [selected, t]);

  const handleRetry = useCallback(async (expenseId: string) => {
    setActionError(null);
    try {
      await retryExport(expenseId);
      const res = await getExports();
      setExports(res.items);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : t("configure.retryFailed"));
    }
  }, [t]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
        <p className="text-muted-foreground">{t("loading")}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center gap-2">
        <p className="text-destructive">{error}</p>
      </div>
    );
  }

  const selectedSystem = systems.find((s) => s.system_name === selected);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-4xl mx-auto px-4 py-6">
        <h1 className="text-2xl font-bold mb-6">{t("title")}</h1>

        {actionError && (
          <div className="mb-4 p-3 rounded bg-destructive/10 text-destructive text-sm">
            {actionError}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="space-y-3">
            <h2 className="text-lg font-semibold">{t("available")}</h2>
            {systems.map((sys) => (
              <IntegrationCard
                key={sys.system_name}
                systemName={sys.system_name}
                displayName={sys.display_name_ar}
                status={status?.system_name === sys.system_name ? (status.status || null) : null}
                lastSyncAt={status?.last_sync_at || null}
                onClick={() => setSelected(sys.system_name)}
                active={selected === sys.system_name}
              />
            ))}
          </div>

          <div className="lg:col-span-2 space-y-4">
            {status && <ConnectionStatus status={status.status || null} lastError={status.last_error || null} />}

            {selectedSystem && (
              <ConfigForm
                systemName={selectedSystem.system_name}
                requiredFields={selectedSystem.required_fields}
                onSave={handleSave}
                onTest={handleTest}
                testing={testing}
                testResult={testResult}
              />
            )}

            <ExportStatusList items={exports} onRetry={handleRetry} />
          </div>
        </div>
      </div>
    </div>
  );
}

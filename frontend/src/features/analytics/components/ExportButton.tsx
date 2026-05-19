import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/lib/auth";
import { getExportUrl } from "../api";

interface Props {
  period: number;
}

export default function ExportButton({ period }: Props) {
  const { t } = useTranslation("analytics");
  const accessToken = useAuthStore((s) => s.accessToken);
  const [open, setOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleExport = (format: "csv" | "excel", view: string) => {
    if (!accessToken) return;
    setDownloading(true);
    setExportError(null);
    const url = getExportUrl(format, view, period);
    fetch(url, { headers: { Authorization: `Bearer ${accessToken}` } })
      .then((res) => {
        if (!res.ok) throw new Error(t("export.failed"));
        return res.blob();
      })
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `analytics-${view}-${period}d.${format === "excel" ? "xlsx" : "csv"}`;
        a.click();
        URL.revokeObjectURL(a.href);
      })
      .catch((err) => setExportError(err.message))
      .finally(() => {
        setDownloading(false);
        setOpen(false);
      });
  };

  const views = [
    { key: "spend-by-project", label: t("charts.spendByProject") },
    { key: "spend-by-category", label: t("charts.spendByCategory") },
    { key: "spend-trend", label: t("charts.spendTrend") },
    { key: "budget-vs-actual", label: t("charts.budgetVsActual") },
  ];

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => { setOpen(!open); setExportError(null); }}
        disabled={downloading}
        aria-haspopup="menu"
        aria-expanded={open}
        className="px-4 py-2 bg-secondary hover:bg-secondary/80 rounded transition-colors text-sm min-h-[44px] disabled:opacity-50"
      >
        {downloading ? t("export.downloading") : t("export.title")}
      </button>

      {exportError && (
        <p className="absolute end-0 top-full mt-1 text-xs text-destructive whitespace-nowrap">{exportError}</p>
      )}

      {open && (
        <div className="absolute end-0 top-full mt-2 bg-popover border border-border rounded-lg shadow-xl z-50 min-w-[200px]" role="menu">
          {views.map((view) => (
            <div key={view.key} className="border-b border-border last:border-0">
              <p className="px-3 pt-2 pb-1 text-xs text-muted-foreground">{view.label}</p>
              <div className="flex gap-1 px-3 pb-2">
                <button
                  role="menuitem"
                  onClick={() => handleExport("csv", view.key)}
                  className="flex-1 px-2 py-1 bg-secondary hover:bg-secondary/80 rounded text-xs min-h-[36px]"
                >
                  CSV
                </button>
                <button
                  role="menuitem"
                  onClick={() => handleExport("excel", view.key)}
                  className="flex-1 px-2 py-1 bg-secondary hover:bg-secondary/80 rounded text-xs min-h-[36px]"
                >
                  Excel
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

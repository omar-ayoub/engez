import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { useLiveQuery } from "dexie-react-hooks";
import { db, type OfflineExpense } from "@/lib/db";
import ExpenseForm from "../components/ExpenseForm";
import { parseLineItems, type ExpenseFormValues } from "../hooks/useExpenseForm";
import { ArrowRight, Trash2, Home as HomeIcon, Receipt, Settings, Clock, Check, Send } from "lucide-react";

export default function DraftReviewPage() {
  const { t } = useTranslation(["capture", "common"]);
  const navigate = useNavigate();
  const [selectedDraft, setSelectedDraft] = useState<OfflineExpense | null>(null);

  const expenses = useLiveQuery(
    () =>
      db.expenses
        .where("status")
        .anyOf(["draft", "pending"])
        .reverse()
        .sortBy("createdAt"),
    [],
    []
  );

  const handleDiscard = async (id: string) => {
    if (!window.confirm(t("capture:sync.confirmDiscard"))) return;
    await db.expenses.delete(id);
  };

  if (selectedDraft) {
    const lineItems = parseLineItems(selectedDraft.items || "");
    const initialData: Partial<ExpenseFormValues> = {
      amount: selectedDraft.amount || 0,
      vendor: selectedDraft.vendor || "",
      lineItems,
      captureMode: (selectedDraft.captureMode as ExpenseFormValues["captureMode"]) || "manual",
    };

    return (
      <div className="flex min-h-svh flex-col bg-background text-foreground">
        <header className="flex items-center gap-3 border-b border-border px-4 py-3">
          <button
            type="button"
            onClick={() => setSelectedDraft(null)}
            className="touch-target inline-flex items-center justify-center rounded-lg p-2 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={t("common:common.back")}
          >
            <ArrowRight className="size-5 ltr:rotate-180" />
          </button>
          <h1 className="text-base font-semibold">{t("capture:sync.reviewDrafts")}</h1>
        </header>
        <div className="flex-1 overflow-y-auto">
          <ExpenseForm
            initialData={initialData}
            initialReceiptBlob={selectedDraft.receiptBlob}
            initialVoiceBlob={selectedDraft.voiceBlob}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-svh flex-col bg-background text-foreground">
      <header className="flex items-center gap-3 border-b border-border px-4 py-3">
        <h1 className="text-base font-semibold">{t("common:nav.expenses")}</h1>
      </header>

      <div className="flex-1 overflow-y-auto p-4">
        {expenses.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <Receipt className="size-10 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">
              {t("capture:sync.noDrafts")}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {expenses.map((expense) => (
              <button
                key={expense.id}
                type="button"
                onClick={() => setSelectedDraft(expense)}
                className="flex items-center gap-3 rounded-xl border border-border bg-card p-3 text-start transition-colors active:bg-accent/50"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-lg tabular-nums" dir="ltr">
                      {expense.amount || "-"}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {expense.currency}
                    </span>
                    <StatusBadge status={expense.status} t={t} />
                  </div>
                  {expense.vendor && (
                    <p className="truncate text-sm text-foreground/80">{expense.vendor}</p>
                  )}
                  {expense.items && (
                    <p className="truncate text-xs text-muted-foreground">{expense.items}</p>
                  )}
                </div>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDiscard(expense.id);
                  }}
                  className="touch-target shrink-0 rounded-lg p-2 text-muted-foreground hover:text-destructive"
                  aria-label={t("capture:sync.delete")}
                >
                  <Trash2 className="size-4" />
                </button>
              </button>
            ))}
          </div>
        )}
      </div>

      <nav
        className="flex items-center justify-around border-t border-border px-2 py-1"
        style={{ paddingBottom: "max(0.25rem, env(safe-area-inset-bottom))" }}
      >
        <NavItem icon={HomeIcon} label={t("common:nav.home")} onPress={() => navigate("/")} />
        <NavItem icon={Receipt} label={t("common:nav.expenses")} active onPress={() => navigate("/drafts")} />
        <NavItem icon={Settings} label={t("common:nav.settings")} onPress={() => navigate("/settings/integrations")} />
      </nav>
    </div>
  );
}

function StatusBadge({ status, t }: { status: string; t: (key: string) => string }) {
  if (status === "draft") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-500">
        <Clock className="size-3" />
        {t("common:expense.pending")}
      </span>
    );
  }
  if (status === "pending") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-brand/15 px-2 py-0.5 text-[10px] font-medium text-brand">
        <Send className="size-3" />
        {t("common:status.syncing")}
      </span>
    );
  }
  if (status === "synced") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-success/15 px-2 py-0.5 text-[10px] font-medium text-success">
        <Check className="size-3" />
        {t("common:expense.synced")}
      </span>
    );
  }
  return null;
}

function NavItem({
  icon: Icon,
  label,
  active = false,
  onPress,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  active?: boolean;
  onPress?: () => void;
}) {
  return (
    <button
      onClick={onPress}
      aria-current={active ? "page" : undefined}
      className={`touch-target flex flex-col items-center justify-center gap-0.5 rounded-lg px-4 py-2 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
        active
          ? "font-medium text-brand"
          : "text-muted-foreground hover:text-foreground"
      }`}
    >
      <Icon className="size-5" />
      <span>{label}</span>
    </button>
  );
}

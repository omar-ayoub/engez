import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useLiveQuery } from "dexie-react-hooks";
import { db, type OfflineExpense } from "@/lib/db";
import ConfidenceBadge from "../components/ConfidenceBadge";
import ExpenseForm from "../components/ExpenseForm";
import type { ExpenseFormValues } from "../hooks/useExpenseForm";
import { ArrowRight, Trash2, RotateCcw } from "lucide-react";

export default function DraftReviewPage() {
  const { t } = useTranslation("capture");
  const [selectedDraft, setSelectedDraft] = useState<OfflineExpense | null>(null);

  const drafts = useLiveQuery(
    () =>
      db.expenses
        .where("status")
        .equals("draft")
        .filter((e) => e.draftProcessed && e.aiExtraction != null)
        .toArray(),
    [],
    []
  );

  const handleDiscard = async (id: string) => {
    if (!window.confirm(t("sync.confirmDiscard"))) return;
    await db.expenses.delete(id);
  };

  const handleRetry = async (id: string) => {
    await db.expenses.update(id, { draftProcessed: false, syncError: undefined });
  };

  if (selectedDraft) {
    const extraction = selectedDraft.aiExtraction as Record<string, unknown> | undefined;
    const itemsStr = (extraction?.items as string) || "";
    const lineItems = itemsStr
      ? itemsStr.split("\n").filter(Boolean).map((line) => ({ description: line, amount: "" }))
      : [{ description: "", amount: "" }];
    const initialData: Partial<ExpenseFormValues> = {
      amount: (extraction?.amount as number) || 0,
      vendor: (extraction?.vendor as string) || "",
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
            aria-label={t("form.back", { defaultValue: "Back" })}
          >
            <ArrowRight className="size-5 ltr:rotate-180" />
          </button>
          <h1 className="text-base font-semibold">{t("sync.reviewDrafts")}</h1>
        </header>
        <ExpenseForm initialData={initialData} />
      </div>
    );
  }

  return (
    <div className="flex min-h-svh flex-col bg-background text-foreground">
      <header className="flex items-center gap-3 border-b border-border px-4 py-3">
        <h1 className="text-base font-semibold">{t("sync.reviewDrafts")}</h1>
      </header>

      <div className="flex-1 p-4">
        {drafts.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <span className="text-3xl">&#10003;</span>
            <p className="text-sm text-muted-foreground">
              {t("sync.noDrafts")}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {drafts.map((draft) => {
              const extraction = draft.aiExtraction as Record<string, unknown> | undefined;
              const confidence = draft.aiConfidence as Record<string, number> | undefined;
              return (
                <button
                  key={draft.id}
                  type="button"
                  onClick={() => setSelectedDraft(draft)}
                  className="flex items-center gap-3 rounded-xl border border-border bg-card p-3 text-start transition-colors active:bg-accent/50"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-lg tabular-nums" dir="ltr">
                        {String(extraction?.amount ?? "-")}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {extraction?.vendor as string || ""}
                      </span>
                      {confidence?.amount != null && (
                        <ConfidenceBadge score={confidence.amount} />
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {extraction?.items as string || ""}
                    </p>
                  </div>

                  <div className="flex gap-1">
                    {draft.syncError && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRetry(draft.id);
                        }}
                        className="touch-target rounded-lg p-2 text-muted-foreground"
                        aria-label={t("sync.retry")}
                      >
                        <RotateCcw className="size-4" />
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDiscard(draft.id);
                      }}
                      className="touch-target rounded-lg p-2 text-muted-foreground"
                      aria-label={t("sync.delete")}
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

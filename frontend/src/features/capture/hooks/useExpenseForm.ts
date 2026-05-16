import { useState, useEffect, useCallback, useRef } from "react";
import { useForm } from "react-hook-form";
import { db, type OfflineExpense } from "@/lib/db";
import { useAuthStore } from "@/lib/auth";

export interface ExpenseFormValues {
  amount: number;
  currency: string;
  vendor: string;
  items: string;
  categoryId: string;
  projectId: string;
  notes: string;
  captureMode: "voice" | "receipt" | "combined" | "manual";
}

interface UseExpenseFormOptions {
  initialData?: Partial<ExpenseFormValues>;
  confidence?: Record<string, number>;
  onSubmitSuccess?: () => void;
}

export function useExpenseForm(options: UseExpenseFormOptions = {}) {
  const [draftId, setDraftId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const autoSaveTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const userId = useAuthStore((s) => s.user?.id ?? "");

  const form = useForm<ExpenseFormValues>({
    defaultValues: {
      amount: options.initialData?.amount ?? 0,
      currency: options.initialData?.currency ?? "EGP",
      vendor: options.initialData?.vendor ?? "",
      items: options.initialData?.items ?? "",
      categoryId: options.initialData?.categoryId ?? "",
      projectId: options.initialData?.projectId ?? "",
      notes: options.initialData?.notes ?? "",
      captureMode: options.initialData?.captureMode ?? "manual",
    },
  });

  const saveDraft = useCallback(async () => {
    const values = form.getValues();
    if (!values.amount && !values.vendor && !values.items) return;

    const now = new Date();
    const id = draftId || crypto.randomUUID();
    const captureMode = values.captureMode || "manual";
    const expense: Partial<OfflineExpense> = {
      id,
      userId,
      amount: values.amount || 0,
      currency: values.currency || "EGP",
      vendor: values.vendor || undefined,
      items: values.items || "",
      categoryId: values.categoryId || undefined,
      projectId: values.projectId || undefined,
      notes: values.notes || undefined,
      captureMode,
      status: "draft",
      etaVerified: false,
      draftProcessed: captureMode === "manual",
      createdAt: now,
    };

    await db.expenses.put(expense as OfflineExpense);
    if (!draftId) setDraftId(id);
  }, [form, draftId, userId]);

  useEffect(() => {
    autoSaveTimerRef.current = setInterval(() => {
      if (form.formState.isDirty) {
        saveDraft();
      }
    }, 5000);

    return () => {
      if (autoSaveTimerRef.current) clearInterval(autoSaveTimerRef.current);
    };
  }, [form.formState.isDirty, saveDraft]);

  const onSubmit = form.handleSubmit(async (values) => {
    setIsSubmitting(true);
    try {
      const now = new Date();
      const id = draftId || crypto.randomUUID();

      if (!values.amount) {
        form.setError("amount", { message: "Amount is required" });
        return;
      }

      const expense: Partial<OfflineExpense> = {
        id,
        userId,
        amount: values.amount,
        currency: values.currency,
        vendor: values.vendor || undefined,
        items: values.items,
        categoryId: values.categoryId || undefined,
        projectId: values.projectId || undefined,
        notes: values.notes || undefined,
        captureMode: values.captureMode,
        status: "pending",
        etaVerified: false,
        draftProcessed: true,
        createdAt: new Date(),
      };

      await db.expenses.put(expense as OfflineExpense);
      await db.syncQueue.add({
        id: crypto.randomUUID(),
        type: "expense",
        payload: JSON.stringify({ ...expense, offline_id: id }),
        retryCount: 0,
        createdAt: now,
      });

      if ("serviceWorker" in navigator) {
        const sw = await navigator.serviceWorker.ready;
        if ("sync" in sw) {
          (sw as unknown as { sync: { register: (tag: string) => void } }).sync.register("expense-sync");
        }
      }

      options.onSubmitSuccess?.();
    } finally {
      setIsSubmitting(false);
    }
  });

  return {
    form,
    draftId,
    isSubmitting,
    onSubmit,
    saveDraft,
    confidence: options.confidence,
  };
}

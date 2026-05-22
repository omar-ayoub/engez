import { useState, useEffect, useCallback, useRef } from "react";
import { useForm } from "react-hook-form";
import { db, type OfflineExpense } from "@/lib/db";
import { useAuthStore } from "@/lib/auth";

export interface LineItem {
  description: string;
  amount: string;
  source: "extracted" | "manual";
}

export interface ExpenseFormValues {
  amount: number;
  currency: string;
  vendor: string;
  lineItems: LineItem[];
  categoryId: string;
  projectId: string;
  notes: string;
  captureMode: "voice" | "receipt" | "combined" | "manual";
}

function serializeLineItems(lineItems: LineItem[]): string {
  return lineItems
    .filter((li) => li.description.trim())
    .map((li) => {
      const prefix = li.source === "manual" ? "[+] " : "";
      const amt = li.amount ? ` — ${li.amount}` : "";
      return `${prefix}${li.description}${amt}`;
    })
    .join("\n");
}

export function parseLineItems(items: string): LineItem[] {
  if (!items) return [{ description: "", amount: "", source: "manual" }];
  const lines = items.split("\n").filter(Boolean);
  if (!lines.length) return [{ description: "", amount: "", source: "manual" }];
  return lines.map((line) => {
    const isManual = line.startsWith("[+] ");
    const clean = isManual ? line.slice(4) : line;
    const dashIdx = clean.lastIndexOf(" — ");
    if (dashIdx >= 0) {
      return {
        description: clean.slice(0, dashIdx),
        amount: clean.slice(dashIdx + 3),
        source: isManual ? "manual" as const : "extracted" as const,
      };
    }
    return { description: clean, amount: "", source: isManual ? "manual" as const : "extracted" as const };
  });
}

interface UseExpenseFormOptions {
  initialData?: Partial<ExpenseFormValues>;
  confidence?: Record<string, number>;
  onSubmitSuccess?: () => void;
  receiptBlob?: Blob | null;
  voiceBlob?: Blob | null;
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
      lineItems: options.initialData?.lineItems ?? [{ description: "", amount: "", source: "manual" }],
      categoryId: options.initialData?.categoryId ?? "",
      projectId: options.initialData?.projectId ?? "",
      notes: options.initialData?.notes ?? "",
      captureMode: options.initialData?.captureMode ?? "manual",
    },
  });

  // Update form when initialData changes (e.g. after AI extraction)
  const initialData = options.initialData;
  const lineItemsDep = JSON.stringify(initialData?.lineItems);
  useEffect(() => {
    if (!initialData) return;
    if (initialData.amount != null) form.setValue("amount", initialData.amount);
    if (initialData.vendor) form.setValue("vendor", initialData.vendor);
    if (initialData.lineItems?.length) form.setValue("lineItems", initialData.lineItems);
    if (initialData.categoryId) form.setValue("categoryId", initialData.categoryId);
    if (initialData.captureMode) form.setValue("captureMode", initialData.captureMode);
  }, [initialData?.amount, initialData?.vendor, lineItemsDep, initialData?.categoryId, initialData?.captureMode, form]);

  const saveDraft = useCallback(async () => {
    const values = form.getValues();
    if (!values.amount && !values.vendor && !values.lineItems.some((li) => li.description.trim())) return;

    const now = new Date();
    const id = draftId || crypto.randomUUID();
    const captureMode = values.captureMode || "manual";
    const expense: Partial<OfflineExpense> = {
      id,
      userId,
      amount: values.amount || 0,
      currency: values.currency || "EGP",
      vendor: values.vendor || undefined,
      items: serializeLineItems(values.lineItems),
      categoryId: values.categoryId || undefined,
      projectId: values.projectId || undefined,
      notes: values.notes || undefined,
      captureMode,
      status: "draft",
      etaVerified: false,
      draftProcessed: captureMode === "manual",
      receiptBlob: options.receiptBlob || undefined,
      voiceBlob: options.voiceBlob || undefined,
      createdAt: now,
    };

    await db.expenses.put(expense as OfflineExpense);
    if (!draftId) setDraftId(id);
  }, [form, draftId, userId]);

  // Keep a ref to the latest saveDraft so the unmount effect can call it
  const saveDraftRef = useRef(saveDraft);
  useEffect(() => { saveDraftRef.current = saveDraft; }, [saveDraft]);

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

  // Save draft on unmount so no data is lost when navigating away
  useEffect(() => {
    return () => { saveDraftRef.current(); };
  }, []);

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
        items: serializeLineItems(values.lineItems),
        categoryId: values.categoryId || undefined,
        projectId: values.projectId || undefined,
        notes: values.notes || undefined,
        captureMode: values.captureMode,
        status: "pending",
        etaVerified: false,
        draftProcessed: true,
        receiptBlob: options.receiptBlob || undefined,
        voiceBlob: options.voiceBlob || undefined,
        createdAt: new Date(),
      };

      await db.expenses.put(expense as OfflineExpense);

      const syncPayload = {
        offline_id: id,
        amount: values.amount,
        currency: values.currency,
        vendor: values.vendor || "",
        items: serializeLineItems(values.lineItems),
        category_id: values.categoryId || null,
        project_id: values.projectId || null,
        notes: values.notes || null,
        capture_mode: values.captureMode,
        eta_verified: false,
        has_manual_items: values.lineItems.some((li) => li.source === "manual" && li.description.trim()),
      };
      await db.syncQueue.add({
        id: crypto.randomUUID(),
        type: "expense",
        payload: JSON.stringify(syncPayload),
        retryCount: 0,
        createdAt: now,
      });

      if ("serviceWorker" in navigator && navigator.serviceWorker.controller) {
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

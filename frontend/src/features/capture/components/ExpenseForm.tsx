import { useState, useCallback, useEffect } from "react";
import { useFieldArray } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useExpenseForm, type ExpenseFormValues, type LineItem } from "../hooks/useExpenseForm";
import VoiceRecordButton, { type VoiceExtractionResult } from "./VoiceRecordButton";
import ReceiptCamera, { type ReceiptExtractionResult } from "./ReceiptCamera";
import CategoryGrid from "./CategoryGrid";
import VendorAutocomplete from "./VendorAutocomplete";
import ConfidenceBadge from "./ConfidenceBadge";
import { confidenceBorderClass } from "../utils/confidence";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import SpeechInputButton from "./SpeechInputButton";
import { QrCode, AlertCircle, Plus, X, Bot, PenLine } from "lucide-react";

interface ExpenseFormProps {
  initialData?: Partial<ExpenseFormValues>;
  confidence?: Record<string, number>;
  onSubmitSuccess?: () => void;
  children?: React.ReactNode;
  initialReceiptBlob?: Blob | null;
  initialVoiceBlob?: Blob | null;
}

export default function ExpenseForm({ initialData, confidence: externalConfidence, onSubmitSuccess, children, initialReceiptBlob, initialVoiceBlob }: ExpenseFormProps) {
  const { t } = useTranslation("capture");
  const [confidence, setConfidence] = useState<Record<string, number> | undefined>(externalConfidence);
  const [etaVerified, setEtaVerified] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(initialData?.categoryId ?? "");
  const [error, setError] = useState<string | null>(null);

  // Sync category and blobs when props change (e.g. after AI extraction)
  useEffect(() => {
    if (initialData?.categoryId) setSelectedCategory(initialData.categoryId);
  }, [initialData?.categoryId]);
  const [receiptBlob, setReceiptBlob] = useState<Blob | null>(initialReceiptBlob ?? null);
  const [voiceBlob, setVoiceBlob] = useState<Blob | null>(initialVoiceBlob ?? null);
  useEffect(() => { if (initialReceiptBlob) setReceiptBlob(initialReceiptBlob); }, [initialReceiptBlob]);
  useEffect(() => { if (initialVoiceBlob) setVoiceBlob(initialVoiceBlob); }, [initialVoiceBlob]);
  const { form, onSubmit, isSubmitting } = useExpenseForm({ initialData, onSubmitSuccess, receiptBlob, voiceBlob });
  const { register, setValue, formState: { errors } } = form;

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "lineItems",
  });

  // Auto-sum line item amounts into total
  useEffect(() => {
    const { unsubscribe } = form.watch((values) => {
      if (!values.lineItems) return;
      const sum = values.lineItems.reduce((acc, li) => {
        const n = parseFloat(li?.amount ?? "");
        return acc + (Number.isFinite(n) ? n : 0);
      }, 0);
      if (sum > 0) setValue("amount", sum);
    });
    return unsubscribe;
  }, [form, setValue]);

  const handleVoiceExtraction = useCallback(
    (result: VoiceExtractionResult, blob?: Blob) => {
      if (blob) setVoiceBlob(blob);
      setError(null);
      if (result.extraction) {
        const e = result.extraction;
        if (e.amount != null) setValue("amount", e.amount);
        if (e.vendor) setValue("vendor", e.vendor);
        if (e.items) {
          const lines = e.items.split("\n").filter(Boolean);
          const lineItems: LineItem[] = lines.map((line) => ({ description: line, amount: "", source: "extracted" }));
          setValue("lineItems", lineItems.length ? lineItems : [{ description: e.items, amount: "", source: "extracted" }]);
        }
        if (e.currency) setValue("currency", e.currency);
        if (e.category) {
          setValue("categoryId", e.category);
          setSelectedCategory(e.category);
        }
        if (e.confidence) setConfidence(e.confidence as Record<string, number>);
      } else if (!result.transcript) {
        setError(t("voice.noSpeech"));
      }
    },
    [setValue, t]
  );

  const handleVoiceError = useCallback((err: string) => {
    setError(err);
  }, []);

  const handleReceiptExtraction = useCallback(
    (result: ReceiptExtractionResult, blob?: Blob) => {
      if (blob) setReceiptBlob(blob);
      setError(null);
      if (result.extraction) {
        const e = result.extraction;
        if (e.amount != null) setValue("amount", e.amount);
        if (e.vendor) setValue("vendor", e.vendor);
        if (e.line_items && e.line_items.length > 0) {
          const lineItems: LineItem[] = e.line_items.map((li) => ({
            description: li.quantity != null && li.quantity > 1 ? `${li.quantity}x ${li.description}` : li.description,
            amount: li.amount != null ? String(li.amount) : "",
            source: "extracted",
          }));
          setValue("lineItems", lineItems);
        } else if (e.items) {
          setValue("lineItems", [{ description: e.items, amount: "", source: "extracted" }]);
        }
        if (e.vendor_tax_reg && e.vendor) setValue("vendor", e.vendor);
        if (e.date) setValue("notes", e.date);
        if (e.category) {
          setValue("categoryId", e.category);
          setSelectedCategory(e.category);
        }
        if (e.confidence) setConfidence(e.confidence as Record<string, number>);
      } else {
        setError(t("receipt.unreadable"));
      }
      if (result.qr_detected) {
        setEtaVerified(true);
        setValue("captureMode", "receipt");
      }
    },
    [setValue, t]
  );

  const handleReceiptError = useCallback((err: string) => {
    setError(err);
  }, []);

  const handleCategoryChange = useCallback(
    (categoryId: string) => {
      setSelectedCategory(categoryId);
      setValue("categoryId", categoryId);
    },
    [setValue]
  );

  const handleVendorChange = useCallback(
    (value: string) => {
      setValue("vendor", value);
    },
    [setValue]
  );

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4 p-4">
      {!children && (
        <div className="flex gap-3">
          <VoiceRecordButton onExtraction={handleVoiceExtraction} onError={handleVoiceError} />
          <ReceiptCamera onExtraction={handleReceiptExtraction} onError={handleReceiptError} />
        </div>
      )}

      {error && (
        <div role="alert" className="flex items-center gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="size-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {etaVerified && (
        <div className="flex items-center gap-1.5 rounded-lg bg-success/10 px-3 py-1.5 text-xs text-success">
          <QrCode className="size-3.5" />
          {t("receipt.qrDetected")}
        </div>
      )}

      {children}

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-1.5">
          <label htmlFor="amount" className="text-sm font-medium text-foreground">
            {t("form.amount")}
          </label>
          {confidence?.amount != null && <ConfidenceBadge score={confidence.amount} />}
        </div>
        <div className="flex items-center gap-2">
          <Input
            id="amount"
            type="text"
            inputMode="decimal"
            dir="ltr"
            className={`h-14 flex-1 text-2xl font-mono tabular-nums ${confidenceBorderClass(confidence?.amount)}`}
            aria-invalid={!!errors.amount}
            aria-describedby={errors.amount ? "amount-error" : undefined}
            {...register("amount", { required: t("form.amount") })}
          />
          <SpeechInputButton onResult={(text) => setValue("amount", text as unknown as number)} className="size-10" />
        </div>
        {errors.amount && (
          <p id="amount-error" className="text-xs text-destructive">{errors.amount.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-1.5">
          <label htmlFor="vendor" className="text-sm font-medium text-foreground">
            {t("form.vendor")}
          </label>
          {confidence?.vendor != null && <ConfidenceBadge score={confidence.vendor} />}
        </div>
        <div className="flex items-start gap-2">
          <div className="flex-1">
            <VendorAutocomplete onChange={handleVendorChange} value={form.watch("vendor")} />
          </div>
          <SpeechInputButton onResult={(text) => handleVendorChange(text)} className="mt-2 size-10" />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-1.5">
          <label className="text-sm font-medium text-foreground">
            {t("form.items")}
          </label>
          {confidence?.items != null && <ConfidenceBadge score={confidence.items} />}
        </div>

        <div className="flex flex-col gap-2 rounded-lg border border-input p-3">
          {fields.length > 0 && (
            <div className="grid grid-cols-[1.25rem_1fr_5rem_2rem] gap-2 text-xs text-muted-foreground">
              <span />
              <span>{t("form.itemDescription")}</span>
              <span className="text-end">{t("form.itemAmount")}</span>
              <span />
            </div>
          )}

          {fields.map((field, index) => (
            <div key={field.id} className="grid grid-cols-[1.25rem_1fr_5rem_2rem] items-center gap-2">
              <span
                className="inline-flex size-5 items-center justify-center"
                title={field.source === "manual" ? t("form.sourceManual") : t("form.sourceExtracted")}
              >
                {field.source === "manual" ? (
                  <PenLine className="size-3.5 text-amber-500" />
                ) : (
                  <Bot className="size-3.5 text-brand" />
                )}
              </span>
              <div className="flex items-center gap-1">
                <Input
                  {...register(`lineItems.${index}.description`)}
                  placeholder={t("form.itemDescriptionPlaceholder")}
                  className="h-10 flex-1 text-sm"
                />
                <SpeechInputButton onResult={(text) => setValue(`lineItems.${index}.description`, text)} className="size-8" />
              </div>
              <Input
                {...register(`lineItems.${index}.amount`)}
                type="text"
                inputMode="decimal"
                dir="ltr"
                placeholder="0"
                className="h-10 text-sm font-mono tabular-nums text-end"
              />
              <button
                type="button"
                onClick={() => fields.length > 1 ? remove(index) : setValue(`lineItems.${index}`, { description: "", amount: "", source: "manual" })}
                className="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label={t("form.removeItem")}
              >
                <X className="size-4" />
              </button>
              <input type="hidden" {...register(`lineItems.${index}.source`)} />
            </div>
          ))}

          <button
            type="button"
            onClick={() => append({ description: "", amount: "", source: "manual" })}
            className="flex min-h-[2.5rem] items-center justify-center gap-1.5 rounded-md border border-dashed border-input text-sm text-muted-foreground transition-colors hover:border-brand hover:text-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Plus className="size-4" />
            {t("form.addItem")}
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-1.5">
          <label htmlFor="category-grid" className="text-sm font-medium text-foreground">
            {t("form.category")}
          </label>
          {confidence?.category != null && <ConfidenceBadge score={confidence.category} />}
        </div>
        <CategoryGrid selected={selectedCategory} onChange={handleCategoryChange} />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="projectId" className="text-sm font-medium text-foreground">
          {t("form.project")}
        </label>
        <select
          id="projectId"
          className="flex min-h-touch w-full rounded-md border border-input bg-transparent px-3 py-2 text-base shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:bg-input/30 md:text-sm"
          {...register("projectId")}
        >
          <option value="">{t("form.project")}</option>
        </select>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="notes" className="text-sm font-medium text-foreground">
          {t("form.notes")}
        </label>
        <div className="flex items-start gap-2">
          <textarea
            id="notes"
            className="flex min-h-[80px] flex-1 rounded-md border border-input bg-transparent px-3 py-2 text-base shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:bg-input/30 md:text-sm"
            {...register("notes")}
          />
          <SpeechInputButton
            onResult={(text) => {
              const current = form.getValues("notes");
              setValue("notes", current ? `${current} ${text}` : text);
            }}
            className="mt-2 size-10"
          />
        </div>
      </div>

      <div className="sticky bottom-0 pt-4 pb-safe">
        <Button
          type="submit"
          disabled={isSubmitting}
          className="h-14 w-full rounded-2xl bg-brand text-lg font-semibold text-white hover:bg-brand-light active:scale-[0.97] transition-[colors,transform] focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          {isSubmitting ? t("form.submitting") : t("form.submit")}
        </Button>
      </div>
    </form>
  );
}

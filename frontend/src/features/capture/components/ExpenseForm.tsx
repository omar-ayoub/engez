import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useExpenseForm, type ExpenseFormValues } from "../hooks/useExpenseForm";
import VoiceRecordButton, { type VoiceExtractionResult } from "./VoiceRecordButton";
import ReceiptCamera, { type ReceiptExtractionResult } from "./ReceiptCamera";
import CategoryGrid from "./CategoryGrid";
import VendorAutocomplete from "./VendorAutocomplete";
import ConfidenceBadge from "./ConfidenceBadge";
import { confidenceBorderClass } from "../utils/confidence";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { QrCode, AlertCircle } from "lucide-react";

interface ExpenseFormProps {
  initialData?: Partial<ExpenseFormValues>;
  confidence?: Record<string, number>;
  onSubmitSuccess?: () => void;
  children?: React.ReactNode;
}

export default function ExpenseForm({ initialData, confidence: externalConfidence, onSubmitSuccess, children }: ExpenseFormProps) {
  const { t } = useTranslation("capture");
  const [confidence, setConfidence] = useState<Record<string, number> | undefined>(externalConfidence);
  const [etaVerified, setEtaVerified] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(initialData?.categoryId ?? "");
  const [error, setError] = useState<string | null>(null);
  const { form, onSubmit, isSubmitting } = useExpenseForm({ initialData, onSubmitSuccess });
  const { register, setValue, formState: { errors } } = form;

  const handleVoiceExtraction = useCallback(
    (result: VoiceExtractionResult) => {
      setError(null);
      if (result.extraction) {
        const e = result.extraction;
        if (e.amount != null) setValue("amount", e.amount);
        if (e.vendor) setValue("vendor", e.vendor);
        if (e.items) setValue("items", e.items);
        if (e.currency) setValue("currency", e.currency);
        if (e.category) setValue("captureMode", "voice");
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
    (result: ReceiptExtractionResult) => {
      setError(null);
      if (result.extraction) {
        const e = result.extraction;
        if (e.amount != null) setValue("amount", e.amount);
        if (e.vendor) setValue("vendor", e.vendor);
        if (e.items) setValue("items", e.items);
        if (e.vendor_tax_reg && e.vendor) setValue("vendor", e.vendor);
        if (e.date) setValue("notes", e.date);
        if (e.category) setValue("captureMode", "receipt");
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
      <div className="flex gap-3">
        <VoiceRecordButton onExtraction={handleVoiceExtraction} onError={handleVoiceError} />
        <ReceiptCamera onExtraction={handleReceiptExtraction} onError={handleReceiptError} />
      </div>

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
        <Input
          id="amount"
          type="text"
          inputMode="decimal"
          dir="ltr"
          className={`h-14 text-2xl font-mono tabular-nums ${confidenceBorderClass(confidence?.amount)}`}
          aria-invalid={!!errors.amount}
          aria-describedby={errors.amount ? "amount-error" : undefined}
          {...register("amount", { required: t("form.amount") })}
        />
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
        <VendorAutocomplete onChange={handleVendorChange} value="" />
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-1.5">
          <label htmlFor="items" className="text-sm font-medium text-foreground">
            {t("form.items")}
          </label>
          {confidence?.items != null && <ConfidenceBadge score={confidence.items} />}
        </div>
        <Input
          id="items"
          type="text"
          placeholder={t("form.itemsPlaceholder")}
          className={confidenceBorderClass(confidence?.items)}
          {...register("items")}
        />
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
          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:bg-input/30 md:text-sm"
          {...register("projectId")}
        >
          <option value="">{t("form.project")}</option>
        </select>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="notes" className="text-sm font-medium text-foreground">
          {t("form.notes")}
        </label>
        <textarea
          id="notes"
          className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-base shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:bg-input/30 md:text-sm"
          {...register("notes")}
        />
      </div>

      <div className="sticky bottom-0 pt-4 pb-safe">
        <Button
          type="submit"
          disabled={isSubmitting}
          className="h-14 w-full rounded-2xl bg-brand-surface text-lg font-semibold text-white hover:bg-brand focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          {isSubmitting ? t("form.submitting") : t("form.submit")}
        </Button>
      </div>
    </form>
  );
}

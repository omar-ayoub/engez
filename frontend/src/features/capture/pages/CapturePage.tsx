import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { useCaptureStore } from "../store";
import { mergeExtractions, type ExtractionSource } from "@/lib/extraction-merge";
import ExpenseForm from "../components/ExpenseForm";
import VoiceRecordButton from "../components/VoiceRecordButton";
import ReceiptCamera from "../components/ReceiptCamera";
import { ArrowLeft, Mic, Camera, Combine, PenLine } from "lucide-react";
import type { VoiceExtractionResult } from "../components/VoiceRecordButton";
import type { ReceiptExtractionResult } from "../components/ReceiptCamera";

const MODES = [
  { id: "voice" as const, icon: Mic },
  { id: "receipt" as const, icon: Camera },
  { id: "combined" as const, icon: Combine },
  { id: "manual" as const, icon: PenLine },
];

export default function CapturePage() {
  const { t } = useTranslation("capture");
  const navigate = useNavigate();
  const { currentMode, setMode, voiceResult, receiptResult, setVoiceResult, setReceiptResult, clearAll } = useCaptureStore();

  const handleVoiceExtraction = (result: VoiceExtractionResult, blob: Blob) => {
    setVoiceResult({
      blob,
      transcript: result.transcript,
      extraction: result.extraction as unknown as Record<string, unknown>,
      voice_url: result.voice_url,
    });
  };

  const handleReceiptExtraction = (result: ReceiptExtractionResult) => {
    setReceiptResult({
      blob: new Blob(),
      extraction: result.extraction as unknown as Record<string, unknown>,
      qr_detected: result.qr_detected,
      receipt_url: result.receipt_url,
    });
  };

  const getMergedInitialData = () => {
    if (currentMode === "voice" && voiceResult?.extraction) {
      const e = voiceResult.extraction as Record<string, unknown>;
      return {
        amount: (e.amount as number) || undefined,
        vendor: (e.vendor as string) || undefined,
        items: (e.items as string) || undefined,
        captureMode: "voice" as const,
      };
    }
    if (currentMode === "receipt" && receiptResult?.extraction) {
      const e = receiptResult.extraction as Record<string, unknown>;
      return {
        amount: (e.amount as number) || undefined,
        vendor: (e.vendor as string) || undefined,
        items: (e.items as string) || undefined,
        captureMode: "receipt" as const,
      };
    }
    if (currentMode === "combined" && voiceResult?.extraction && receiptResult?.extraction) {
      const voiceExt = voiceResult.extraction as ExtractionSource;
      const receiptExt = receiptResult.extraction as ExtractionSource;
      const merged = mergeExtractions(voiceExt, {
        extraction: receiptExt,
        qr_detected: receiptResult.qr_detected,
        qr_data: receiptResult.qr_data ?? null,
      });
      return {
        amount: merged.amount || undefined,
        vendor: merged.vendor || undefined,
        items: merged.items || undefined,
        captureMode: "combined" as const,
      };
    }
    return { captureMode: currentMode };
  };

  return (
    <div className="flex min-h-svh flex-col bg-background text-foreground">
      <header className="flex items-center gap-3 border-b border-border px-4 py-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="touch-target inline-flex items-center justify-center rounded-lg p-2 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label={t("form.back", { defaultValue: "Back" })}
        >
          <ArrowLeft className="size-5 rtl:rotate-180" />
        </button>
        <h1 className="text-base font-semibold">{t(`modes.${currentMode}`)}</h1>
      </header>

      <div className="flex justify-around border-b border-border px-2 py-2">
        {MODES.map(({ id, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setMode(id)}
            aria-pressed={currentMode === id}
            className={`flex min-h-touch flex-col items-center justify-center gap-0.5 rounded-lg px-4 py-2 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
              currentMode === id
                ? "font-medium text-brand"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon className="size-5" />
            <span>{t(`modes.${id}`)}</span>
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto">
        <ExpenseForm initialData={getMergedInitialData()} onSubmitSuccess={clearAll}>
          {(currentMode === "voice" || currentMode === "combined") && (
            <VoiceRecordButton onExtraction={handleVoiceExtraction} />
          )}
          {(currentMode === "receipt" || currentMode === "combined") && (
            <ReceiptCamera onExtraction={handleReceiptExtraction} />
          )}
        </ExpenseForm>
      </div>
    </div>
  );
}

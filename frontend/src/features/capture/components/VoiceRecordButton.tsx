import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useVoiceCapture } from "../hooks/useVoiceCapture";
import { Mic, Square, Loader2 } from "lucide-react";

interface VoiceExtractionResult {
  transcript: string | null;
  extraction: {
    amount: number | null;
    currency: string;
    category: string | null;
    vendor: string | null;
    items: string | null;
    project_hint: string | null;
    confidence: Record<string, number | null> | null;
  } | null;
  voice_url: string | null;
}

interface VoiceRecordButtonProps {
  onExtraction: (result: VoiceExtractionResult, blob: Blob) => void;
  onError?: (error: string) => void;
}

export default function VoiceRecordButton({ onExtraction, onError }: VoiceRecordButtonProps) {
  const { t } = useTranslation("capture");
  const { isRecording, duration, start, stop } = useVoiceCapture();
  const [isProcessing, setIsProcessing] = useState(false);

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const handleToggle = async () => {
    if (isProcessing) return;

    if (isRecording) {
      try {
        const { blob } = await stop();
        setIsProcessing(true);

        const formData = new FormData();
        formData.append("audio", blob, "audio.webm");

        const { useAuthStore } = await import("@/lib/auth");
        const token = useAuthStore.getState().accessToken;

        const res = await fetch("/api/v1/voice/extract", {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          credentials: "include",
          body: formData,
        });

        if (!res.ok) {
          const err = await res.json();
          onError?.(err.detail || err.detail_en || t("voice.networkError"));
          return;
        }

        const result: VoiceExtractionResult = await res.json();
        onExtraction(result, blob);
      } catch (e) {
        onError?.(e instanceof Error ? e.message : t("voice.networkError"));
      } finally {
        setIsProcessing(false);
      }
    } else {
      try {
        await start();
      } catch {
        onError?.(t("voice.noPermission"));
      }
    }
  };

  return (
    <button
      type="button"
      onClick={handleToggle}
      disabled={isProcessing}
      className="flex min-h-touch min-w-touch flex-col items-center justify-center gap-1 rounded-2xl border-2 border-dashed border-brand/40 p-4 transition-colors active:bg-brand/10 disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      aria-label={isRecording ? t("voice.stop") : t("voice.record")}
    >
      {isProcessing ? (
        <>
          <Loader2 className="size-8 animate-spin text-brand" />
          <span className="text-xs text-muted-foreground">{t("voice.processing")}</span>
        </>
      ) : isRecording ? (
        <>
          <div className="relative">
            <Square className="size-8 text-danger" />
            <span className="absolute -right-1 -top-1 h-3 w-3 animate-pulse rounded-full bg-danger" />
          </div>
          <span className="font-mono text-sm tabular-nums" dir="ltr">
            {formatDuration(duration)}
          </span>
          <span className="text-xs text-muted-foreground">{t("voice.stop")}</span>
        </>
      ) : (
        <>
          <Mic className="size-8 text-brand" />
          <span className="text-xs text-muted-foreground">{t("voice.record")}</span>
        </>
      )}
    </button>
  );
}

export type { VoiceExtractionResult };

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useReceiptCapture } from "../hooks/useReceiptCapture";
import { Camera, Loader2, QrCode, RotateCcw } from "lucide-react";

interface ReceiptExtractionResult {
  extraction: {
    amount: number | null;
    currency: string;
    vendor: string | null;
    vendor_tax_reg: string | null;
    date: string | null;
    category: string | null;
    items: string | null;
    line_items: Array<{ description: string; quantity: number | null; amount: number | null }>;
    confidence: Record<string, number | null> | null;
  } | null;
  qr_detected: boolean;
  qr_data: {
    uuid: string | null;
    total: number | null;
    issuer_rin: string | null;
    datetime: string | null;
  } | null;
  receipt_url: string | null;
}

interface ReceiptCameraProps {
  onExtraction: (result: ReceiptExtractionResult) => void;
  onError?: (error: string) => void;
}

export default function ReceiptCamera({ onExtraction, onError }: ReceiptCameraProps) {
  const { t } = useTranslation("capture");
  const { imageBlob, previewUrl, isProcessing, capture, reset } = useReceiptCapture();
  const [qrBadge, setQrBadge] = useState(false);

  const handleCapture = () => {
    reset();
    setQrBadge(false);
    capture();
  };

  const processImage = async (blob: Blob) => {
    try {
      const formData = new FormData();
      formData.append("image", blob, "receipt.jpg");

      const { useAuthStore } = await import("@/lib/auth");
      const token = useAuthStore.getState().accessToken;

      const res = await fetch("/api/v1/receipts/extract", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        credentials: "include",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => null);
        onError?.(err?.detail || err?.detail_en || t("receipt.unreadable"));
        return;
      }

      const result: ReceiptExtractionResult = await res.json();
      if (result.qr_detected) setQrBadge(true);
      onExtraction(result);
    } catch {
      onError?.(t("receipt.unreadable"));
    }
  };

  return (
    <div className="flex flex-col items-center gap-2">
      {previewUrl ? (
        <div className="relative">
          <img
            src={previewUrl}
            alt="Receipt preview"
            className="h-24 w-24 rounded-lg object-cover"
          />
          {qrBadge && (
            <span className="absolute -right-1 -top-1 flex items-center gap-0.5 rounded-full bg-success-surface px-1.5 py-0.5 text-[10px] text-white">
              <QrCode className="size-3" />
              {t("receipt.qr")}
            </span>
          )}
          <button
            type="button"
            onClick={handleCapture}
            className="touch-target absolute -bottom-2 -left-2 inline-flex items-center justify-center rounded-full bg-secondary p-2 focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={t("receipt.retake")}
          >
            <RotateCcw className="size-4" />
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={handleCapture}
          disabled={isProcessing}
          className="flex min-h-touch min-w-touch flex-col items-center justify-center gap-1 rounded-2xl border-2 border-dashed border-brand/40 p-4 transition-colors active:bg-brand/10 disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          aria-label={t("receipt.capture")}
        >
          {isProcessing ? (
            <>
              <Loader2 className="size-8 animate-spin text-brand" />
              <span className="text-xs text-muted-foreground">{t("receipt.processing")}</span>
            </>
          ) : (
            <>
              <Camera className="size-8 text-brand" />
              <span className="text-xs text-muted-foreground">{t("receipt.capture")}</span>
            </>
          )}
        </button>
      )}

      {imageBlob && !isProcessing && (
        <button
          type="button"
          onClick={() => processImage(imageBlob)}
          className="min-h-touch rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          {t("receipt.process")}
        </button>
      )}
    </div>
  );
}

export type { ReceiptExtractionResult };

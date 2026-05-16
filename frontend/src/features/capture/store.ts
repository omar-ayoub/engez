import { create } from "zustand";
import { mergeExtractions, type ExtractionSource } from "@/lib/extraction-merge";

type CaptureMode = "voice" | "receipt" | "combined" | "manual";

interface VoiceResult {
  blob: Blob;
  transcript: string | null;
  extraction: Record<string, unknown> | null;
  voice_url: string | null;
}

interface ReceiptResult {
  blob: Blob;
  extraction: Record<string, unknown> | null;
  qr_detected: boolean;
  qr_data?: { total?: number | null; issuer_rin?: string | null; datetime?: string | null } | null;
  receipt_url: string | null;
}

interface CaptureState {
  currentMode: CaptureMode;
  voiceResult: VoiceResult | null;
  receiptResult: ReceiptResult | null;
  mergedExtraction: Record<string, unknown> | null;
  setMode: (mode: CaptureMode) => void;
  setVoiceResult: (result: VoiceResult | null) => void;
  setReceiptResult: (result: ReceiptResult | null) => void;
  clearAll: () => void;
}

function computeMerged(voice: VoiceResult | null, receipt: ReceiptResult | null): Record<string, unknown> | null {
  if (!voice?.extraction && !receipt?.extraction) return null;
  const merged = mergeExtractions(
    voice?.extraction as ExtractionSource | null,
    receipt
      ? {
          extraction: receipt.extraction as ExtractionSource | null,
          qr_detected: receipt.qr_detected,
          qr_data: receipt.qr_data ?? null,
        }
      : null
  );
  return merged as unknown as Record<string, unknown>;
}

export const useCaptureStore = create<CaptureState>((set, get) => ({
  currentMode: "manual",
  voiceResult: null,
  receiptResult: null,
  mergedExtraction: null,

  setMode: (mode) => set({ currentMode: mode }),

  setVoiceResult: (result) => {
    set({ voiceResult: result });
    const { receiptResult } = get();
    set({ mergedExtraction: computeMerged(result, receiptResult) });
  },

  setReceiptResult: (result) => {
    set({ receiptResult: result });
    const { voiceResult } = get();
    set({ mergedExtraction: computeMerged(voiceResult, result) });
  },

  clearAll: () =>
    set({
      voiceResult: null,
      receiptResult: null,
      mergedExtraction: null,
    }),
}));

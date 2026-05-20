import { useState, useRef, useCallback, useEffect } from "react";
import { compressReceiptImage } from "@/lib/image-compress";

interface UseReceiptCaptureReturn {
  imageBlob: Blob | null;
  previewUrl: string | null;
  isProcessing: boolean;
  capture: () => void;
  reset: () => void;
}

export function useReceiptCapture(): UseReceiptCaptureReturn {
  const [imageBlob, setImageBlob] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const capture = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.capture = "environment";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      setIsProcessing(true);
      try {
        const compressed = await compressReceiptImage(file);
        setImageBlob(compressed);
        setPreviewUrl(URL.createObjectURL(compressed));
      } finally {
        setIsProcessing(false);
      }
    };
    input.click();
    inputRef.current = input;
  }, []);

  const reset = useCallback(() => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setImageBlob(null);
    setPreviewUrl(null);
  }, [previewUrl]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  return { imageBlob, previewUrl, isProcessing, capture, reset };
}

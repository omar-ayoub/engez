import { useState, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Mic } from "lucide-react";

// Web Speech API types — not all browsers expose SpeechRecognition on window
type SpeechRecognitionErrorEvent = { error: string; message?: string };
type SpeechRecognitionInstance = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};
type SpeechRecognitionCtor = new () => SpeechRecognitionInstance;

function getSR(): SpeechRecognitionCtor | undefined {
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition) as SpeechRecognitionCtor | undefined;
}

interface SpeechInputButtonProps {
  onResult: (transcript: string) => void;
  onError?: (error: string) => void;
  className?: string;
}

const isSupported = typeof window !== "undefined" && !!getSR();

export default function SpeechInputButton({ onResult, onError, className = "" }: SpeechInputButtonProps) {
  const { i18n, t } = useTranslation("capture");
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);

  const toggle = useCallback(() => {
    if (isListening) {
      recognitionRef.current?.stop();
      return;
    }

    const SR = getSR();
    if (!SR) return;

    const recognition = new SR();
    recognition.lang = i18n.language === "ar" ? "ar-EG" : "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0]?.[0]?.transcript;
      if (transcript) onResult(transcript.trim());
    };
    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      setIsListening(false);
      recognitionRef.current = null;
      // "aborted" is user-initiated, "no-speech" is normal timeout — don't report these
      if (event.error !== "aborted" && event.error !== "no-speech") {
        onError?.(event.error === "not-allowed"
          ? t("voice.noPermission")
          : t("voice.networkError"));
      }
    };
    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
      setIsListening(true);
    } catch {
      setIsListening(false);
      recognitionRef.current = null;
      onError?.(t("voice.noPermission"));
    }
  }, [isListening, i18n.language, onResult, onError, t]);

  if (!isSupported) return null;

  return (
    <button
      type="button"
      onClick={toggle}
      className={`inline-flex shrink-0 items-center justify-center rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
        isListening
          ? "text-brand animate-pulse"
          : "text-muted-foreground hover:text-foreground"
      } ${className}`}
      aria-label={isListening ? t("form.micListening") : t("form.micSpeak")}
      title={isListening ? t("form.micListening") : t("form.micSpeak")}
    >
      <Mic className="size-4" />
    </button>
  );
}

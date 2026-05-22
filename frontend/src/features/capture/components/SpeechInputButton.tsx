import { useState, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Mic } from "lucide-react";

// Web Speech API types — not all browsers expose SpeechRecognition on window
type SpeechRecognitionInstance = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};
type SpeechRecognitionCtor = new () => SpeechRecognitionInstance;

function getSR(): SpeechRecognitionCtor | undefined {
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition) as SpeechRecognitionCtor | undefined;
}

interface SpeechInputButtonProps {
  onResult: (transcript: string) => void;
  className?: string;
}

const isSupported = typeof window !== "undefined" && !!getSR();

export default function SpeechInputButton({ onResult, className = "" }: SpeechInputButtonProps) {
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
      const transcript = event.results[0][0].transcript;
      onResult(transcript.trim());
    };
    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }, [isListening, i18n.language, onResult]);

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

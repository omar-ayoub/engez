import { useEffect } from "react";
import { useTranslation } from "react-i18next";

export function useDirection() {
  const { i18n } = useTranslation();
  const language = i18n.language;
  const dir = language === "ar" ? "rtl" : "ltr";
  const isRTL = dir === "rtl";

  useEffect(() => {
    document.documentElement.dir = dir;
    document.documentElement.lang = language;
  }, [dir, language]);

  return { dir, isRTL, language } as const;
}

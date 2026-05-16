import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import arCommon from "@/locales/ar/common.json";
import enCommon from "@/locales/en/common.json";
import arCapture from "@/locales/ar/capture.json";
import enCapture from "@/locales/en/capture.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: "ar",
    defaultNS: "common",
    ns: ["common", "capture"],
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "engez-lang",
    },
    resources: {
      ar: { common: arCommon, capture: arCapture },
      en: { common: enCommon, capture: enCapture },
    },
  });

export default i18n;

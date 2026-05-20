import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import arCommon from "@/locales/ar/common.json";
import enCommon from "@/locales/en/common.json";
import arCapture from "@/locales/ar/capture.json";
import enCapture from "@/locales/en/capture.json";
import arReview from "@/locales/ar/review.json";
import enReview from "@/locales/en/review.json";
import arAnalytics from "@/locales/ar/analytics.json";
import enAnalytics from "@/locales/en/analytics.json";
import arIntegrations from "@/locales/ar/integrations.json";
import enIntegrations from "@/locales/en/integrations.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: "ar",
    defaultNS: "common",
    ns: ["common", "capture", "review", "analytics", "integrations"],
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "engez-lang",
    },
    resources: {
      ar: { common: arCommon, capture: arCapture, review: arReview, analytics: arAnalytics, integrations: arIntegrations },
      en: { common: enCommon, capture: enCapture, review: enReview, analytics: enAnalytics, integrations: enIntegrations },
    },
  });

export default i18n;

import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import arCommon from "../../public/locales/ar/common.json";
import enCommon from "../../public/locales/en/common.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: "ar",
    defaultNS: "common",
    ns: ["common"],
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "engez-lang",
    },
    resources: {
      ar: { common: arCommon },
      en: { common: enCommon },
    },
  });

export default i18n;

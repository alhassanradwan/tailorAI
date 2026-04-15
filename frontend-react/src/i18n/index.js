import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import en from './locales/en.json';
import ar from './locales/ar.json';

const resources = {
  en: { translation: en },
  ar: { translation: ar },
};

const rtlLanguages = new Set(['ar']);

function applyDocumentLanguage(lng) {
  const language = (lng || 'en').split('-')[0];
  const normalized = language === 'ar' ? 'ar' : 'en';
  const direction = rtlLanguages.has(normalized) ? 'rtl' : 'ltr';

  document.documentElement.lang = normalized;
  document.documentElement.dir = direction;
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    supportedLngs: ['en', 'ar'],
    detection: {
      order: ['localStorage', 'htmlTag'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },
    interpolation: {
      escapeValue: false,
    },
  });

applyDocumentLanguage(i18n.resolvedLanguage || i18n.language || 'en');
i18n.on('languageChanged', applyDocumentLanguage);

export default i18n;

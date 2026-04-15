import { useTranslation } from 'react-i18next';

export default function LanguageSwitcher() {
  const { i18n, t } = useTranslation();

  const currentLanguage = (i18n.resolvedLanguage || i18n.language || 'en').split('-')[0];

  return (
    <div className="language-switcher">
      <label className="language-switcher-label" htmlFor="language-select">{t('common.language')}:</label>
      <select
        id="language-select"
        className="language-switcher-select"
        value={currentLanguage === 'ar' ? 'ar' : 'en'}
        onChange={(e) => i18n.changeLanguage(e.target.value)}
        aria-label={t('languageSwitcher.ariaLabel')}
      >
        <option value="en">{t('common.english')}</option>
        <option value="ar">{t('common.arabic')}</option>
      </select>
    </div>
  );
}

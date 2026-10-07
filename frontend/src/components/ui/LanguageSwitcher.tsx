import React from 'react';
import { useTranslation } from 'react-i18next';

const LOCALES = [
  { code: 'en', label: 'EN', native: 'English', dir: 'ltr' },
  { code: 'ur', label: 'اردو', native: 'اردو', dir: 'rtl' },
] as const;

export const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();
  const currentLocale = i18n.language.startsWith('ur') ? 'ur' : 'en';

  const handleChange = (code: string, dir: string) => {
    i18n.changeLanguage(code);
    localStorage.setItem('agriscope_locale', code);
    document.documentElement.dir = dir;
    document.documentElement.lang = code;
  };

  return (
    <div className="flex items-center rounded-md border border-input bg-background">
      {LOCALES.map((locale, idx) => (
        <button
          key={locale.code}
          onClick={() => handleChange(locale.code, locale.dir)}
          aria-label={`Switch to ${locale.native}`}
          aria-pressed={currentLocale === locale.code}
          className={[
            'px-2.5 py-1 text-xs font-semibold transition-colors',
            idx === 0 ? 'rounded-s-md' : 'rounded-e-md',
            currentLocale === locale.code
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
          ].join(' ')}
        >
          {locale.label}
        </button>
      ))}
    </div>
  );
};

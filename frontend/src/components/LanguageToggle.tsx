'use client';

import React from 'react';
import type { Language } from '@/lib/i18n';
import { getTranslation } from '@/lib/i18n';

interface LanguageToggleProps {
  currentLang: Language;
  onLanguageChange: (lang: Language) => void;
}

export const LanguageToggle: React.FC<LanguageToggleProps> = ({
  currentLang,
  onLanguageChange,
}) => {
  const t = getTranslation(currentLang);

  return (
    <nav aria-label={t.langToggleAria} className="flex items-center">
      <div
        role="group"
        aria-label={t.langToggleAria}
        className="inline-flex items-center rounded-lg bg-cloud p-0.5 text-xs font-medium text-midnight border border-cloud"
      >
        <button
          type="button"
          onClick={() => onLanguageChange('en')}
          aria-pressed={currentLang === 'en'}
          className={`min-h-[44px] min-w-[44px] px-3 py-2 rounded-md transition-colors inline-flex items-center justify-center focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ocean cursor-pointer select-none ${
            currentLang === 'en'
              ? 'bg-white text-midnight font-semibold shadow-xs'
              : 'text-midnight/70 hover:text-midnight'
          }`}
        >
          EN
        </button>
        <span className="text-midnight/30 select-none px-0.5" aria-hidden="true">
          |
        </span>
        <button
          type="button"
          onClick={() => onLanguageChange('hi')}
          aria-pressed={currentLang === 'hi'}
          className={`min-h-[44px] min-w-[44px] px-3 py-2 rounded-md transition-colors font-hind inline-flex items-center justify-center focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ocean cursor-pointer select-none ${
            currentLang === 'hi'
              ? 'bg-white text-midnight font-semibold shadow-xs'
              : 'text-midnight/70 hover:text-midnight'
          }`}
        >
          हिन्दी
        </button>
      </div>
    </nav>
  );
};

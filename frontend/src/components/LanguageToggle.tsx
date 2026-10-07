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
        className="inline-flex items-center rounded-lg bg-cloud p-0.5 text-xs font-medium text-midnight"
      >
        <button
          type="button"
          onClick={() => onLanguageChange('en')}
          aria-pressed={currentLang === 'en'}
          className={`px-2.5 py-1 rounded-md transition-colors focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ocean ${
            currentLang === 'en'
              ? 'bg-white text-midnight font-semibold'
              : 'text-midnight/70 hover:text-midnight'
          }`}
        >
          EN
        </button>
        <span className="text-midnight/30 select-none" aria-hidden="true">
          |
        </span>
        <button
          type="button"
          onClick={() => onLanguageChange('hi')}
          aria-pressed={currentLang === 'hi'}
          className={`px-2.5 py-1 rounded-md transition-colors font-hind focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ocean ${
            currentLang === 'hi'
              ? 'bg-white text-midnight font-semibold'
              : 'text-midnight/70 hover:text-midnight'
          }`}
        >
          हिन्दी
        </button>
      </div>
    </nav>
  );
};

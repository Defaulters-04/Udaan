'use client';

import React from 'react';
import { useSessionStore } from '@/store/session';
import { LanguageToggle } from '@/components/LanguageToggle';

export interface SiteHeaderProps {
  variant?: 'standard' | 'hero';
  tagline?: string;
}

export const SiteHeader: React.FC<SiteHeaderProps> = ({
  variant = 'standard',
  tagline,
}) => {
  const storeLang = useSessionStore((state) => state.lang);
  const setLang = useSessionStore((state) => state.setLang);

  return (
    <header className="w-full border-b border-cloud">
      <div
        className={`flex items-center justify-between ${
          variant === 'hero' ? 'py-8 sm:py-10' : 'py-5 sm:py-6'
        }`}
      >
        <div className="flex flex-col">
          <h1
            className={`font-bricolage font-extrabold text-midnight tracking-[-0.035em] leading-[0.9] select-none [font-optical-sizing:auto] ${
              variant === 'hero'
                ? 'text-[clamp(64px,9vw,96px)]'
                : 'text-[clamp(36px,4.5vw,48px)]'
            }`}
            style={{
              fontFamily: 'var(--font-bricolage), sans-serif',
              fontWeight: 800,
              fontOpticalSizing: 'auto',
            }}
          >
            Udaan
          </h1>
          {variant === 'hero' && tagline && (
            <p className="mt-3 text-base sm:text-lg text-[#3E5470] font-normal leading-relaxed">
              {tagline}
            </p>
          )}
        </div>

        <div className="shrink-0 flex items-center justify-end">
          <LanguageToggle
            currentLang={storeLang}
            onLanguageChange={(lang) => setLang(lang)}
          />
        </div>
      </div>
    </header>
  );
};

// Backwards-compatible alias
export const Header = SiteHeader;

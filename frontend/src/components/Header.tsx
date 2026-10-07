'use client';

import React from 'react';
import Link from 'next/link';
import { useSessionStore } from '@/store/session';
import { LanguageToggle } from '@/components/LanguageToggle';

interface HeaderProps {
  tagline?: string;
  backHref?: string;
  backLabel?: string;
}

export const Header: React.FC<HeaderProps> = ({
  tagline,
  backHref,
  backLabel,
}) => {
  const storeLang = useSessionStore((state) => state.lang);
  const setLang = useSessionStore((state) => state.setLang);

  return (
    <header className="w-full mb-8 sm:mb-12">
      {/* Top action row */}
      <div className="flex items-center justify-between mb-6 sm:mb-8">
        <div>
          {backHref ? (
            <Link
              href={backHref}
              className="text-ocean hover:underline text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ocean rounded px-1 transition-colors"
            >
              ← {backLabel || 'Back'}
            </Link>
          ) : (
            <div aria-hidden="true" className="w-12" />
          )}
        </div>
        <LanguageToggle
          currentLang={storeLang}
          onLanguageChange={(lang) => setLang(lang)}
        />
      </div>

      {/* Udaan wordmark */}
      <div>
        <h1
          className="font-bricolage text-[clamp(3.5rem,8vw,6rem)] leading-[0.92] tracking-tight font-extrabold text-midnight select-none"
          style={{ fontFamily: 'var(--font-bricolage), sans-serif' }}
        >
          Udaan
        </h1>
        {tagline && (
          <p className="mt-3 sm:mt-4 text-base sm:text-lg text-midnight/80 font-normal leading-relaxed">
            {tagline}
          </p>
        )}
      </div>
    </header>
  );
};

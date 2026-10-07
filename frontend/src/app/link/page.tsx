'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { useSessionStore } from '@/store/session';
import { getTranslation } from '@/lib/i18n';
import { LanguageToggle } from '@/components/LanguageToggle';

export default function LinkPlaceholderPage() {
  const storeRole = useSessionStore((state) => state.role);
  const storeName = useSessionStore((state) => state.name);
  const storeLang = useSessionStore((state) => state.lang);
  const hasHydrated = useSessionStore((state) => state.hasHydrated);
  const setLang = useSessionStore((state) => state.setLang);

  useEffect(() => {
    useSessionStore.persist.rehydrate();
  }, []);

  useEffect(() => {
    document.documentElement.lang = storeLang;
  }, [storeLang]);

  const t = getTranslation(storeLang);
  const isStoreEmpty = !storeRole || !storeName;

  // Heading font family based on active language
  const headingFontClass =
    storeLang === 'hi' ? 'font-hind' : 'font-bricolage';

  return (
    <div className="min-h-screen bg-paper text-midnight selection:bg-sky/20 flex flex-col justify-between">
      <main className="w-full max-w-[560px] mx-auto px-5 sm:px-6 pt-8 sm:pt-16 pb-12 flex-1 flex flex-col">
        {/* Top bar with language toggle */}
        <header className="flex items-center justify-between mb-8 sm:mb-12">
          <Link
            href="/"
            className="text-ocean hover:underline text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ocean rounded px-1"
          >
            ← {t.backToWelcome}
          </Link>
          <LanguageToggle
            currentLang={storeLang}
            onLanguageChange={(lang) => setLang(lang)}
          />
        </header>

        {/* Udaan wordmark */}
        <header className="mb-10 sm:mb-14">
          <h1
            className="font-bricolage text-[clamp(3.5rem,8vw,6rem)] leading-[0.92] tracking-tight font-extrabold text-midnight select-none"
            style={{ fontFamily: 'var(--font-bricolage), sans-serif' }}
          >
            Udaan
          </h1>
          <p className="mt-3 sm:mt-4 text-base sm:text-lg text-midnight/80 font-normal leading-relaxed">
            {t.tagline}
          </p>
        </header>

        {/* Main Content */}
        <div className="space-y-8 flex-1">
          {isStoreEmpty && hasHydrated ? (
            <div className="p-6 bg-cloud/50 border border-cloud rounded-xl space-y-4">
              <p className="text-base text-midnight/80">{t.emptyStoreWarning}</p>
              <Link
                href="/"
                className="inline-block px-6 py-3 bg-ocean text-white font-medium text-base rounded-xl hover:bg-[#255ba0] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ocean"
              >
                {t.backToWelcome}
              </Link>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="space-y-2">
                <h2
                  className={`${headingFontClass} text-2xl sm:text-3xl font-bold text-midnight tracking-tight`}
                >
                  {t.page2Next}
                </h2>
                <p className="text-sm sm:text-base text-midnight/70">
                  {t.page2Desc}
                </p>
              </div>

              {/* Saved Session Summary Card */}
              <div className="p-5 sm:p-6 bg-white border-2 border-cloud rounded-xl space-y-4">
                <h3 className="text-sm font-semibold text-midnight/60 uppercase tracking-wide">
                  Saved Session
                </h3>
                <dl className="space-y-3 text-sm sm:text-base">
                  <div className="flex justify-between py-1 border-b border-cloud/60">
                    <dt className="text-midnight/65">{t.savedRole}:</dt>
                    <dd className="font-semibold text-midnight">
                      {storeRole ? t[storeRole] : '—'}
                    </dd>
                  </div>
                  <div className="flex justify-between py-1 border-b border-cloud/60">
                    <dt className="text-midnight/65">{t.savedName}:</dt>
                    <dd className="font-semibold text-midnight">
                      {storeName || '—'}
                    </dd>
                  </div>
                  <div className="flex justify-between py-1">
                    <dt className="text-midnight/65">{t.savedLang}:</dt>
                    <dd className="font-semibold text-midnight">
                      {storeLang === 'hi' ? 'हिन्दी' : 'English'}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
          )}
        </div>

        {/* Footnote */}
        <footer className="mt-14 sm:mt-20 pt-6 border-t border-cloud/70 text-xs sm:text-sm text-midnight/65 leading-relaxed">
          <p>{t.consent}</p>
        </footer>
      </main>
    </div>
  );
}

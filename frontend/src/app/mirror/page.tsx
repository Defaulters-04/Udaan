'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { useSessionStore } from '@/store/session';
import { getTranslation } from '@/lib/i18n';
import { Header } from '@/components/Header';

export default function FamilyMirrorPlaceholderPage() {
  const storeLang = useSessionStore((state) => state.lang);
  const storeRole = useSessionStore((state) => state.role);
  const storeName = useSessionStore((state) => state.name);
  const storeFamily = useSessionStore((state) => state.family);

  useEffect(() => {
    useSessionStore.persist.rehydrate();
  }, []);

  useEffect(() => {
    document.documentElement.lang = storeLang;
  }, [storeLang]);

  const t = getTranslation(storeLang);
  const headingFontClass = storeLang === 'hi' ? 'font-hind' : 'font-bricolage';

  return (
    <div className="min-h-screen bg-paper text-midnight selection:bg-sky/20 flex flex-col justify-between">
      <main className="w-full max-w-[560px] mx-auto px-5 sm:px-6 pt-8 sm:pt-16 pb-12 flex-1 flex flex-col">
        <Header backHref="/assessment" backLabel={t.back} />

        <div className="space-y-6 flex-1">
          <div className="space-y-2">
            <h2
              className={`${headingFontClass} text-2xl sm:text-3xl font-bold text-midnight tracking-tight`}
            >
              {t.page5Next}
            </h2>
            <p className="text-sm sm:text-base text-midnight/70">
              Family Mirror: Overlaid radar charts, conflict gauge & alignment explorer (coming soon)
            </p>
          </div>

          <div className="p-5 sm:p-6 bg-white border-2 border-cloud rounded-xl space-y-3">
            <div className="flex justify-between py-1 border-b border-cloud/60 text-sm">
              <span className="text-midnight/65">{t.savedRole}:</span>
              <span className="font-semibold text-midnight">
                {storeRole ? t[storeRole] : '—'}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-cloud/60 text-sm">
              <span className="text-midnight/65">{t.savedName}:</span>
              <span className="font-semibold text-midnight">{storeName || '—'}</span>
            </div>
            {storeFamily && (
              <div className="flex justify-between py-1 text-sm">
                <span className="text-midnight/65">{t.codeLabel}:</span>
                <span className="font-mono font-bold text-midnight tracking-wider">
                  {storeFamily.code}
                </span>
              </div>
            )}
          </div>

          <div>
            <Link
              href="/"
              className="inline-block px-6 py-2.5 bg-cloud hover:bg-cloud/80 text-midnight text-sm font-medium rounded-xl transition-colors focus-visible:outline-2 focus-visible:outline-ocean"
            >
              {t.backToWelcome}
            </Link>
          </div>
        </div>

        <footer className="mt-14 sm:mt-20 pt-6 border-t border-cloud/70 text-xs sm:text-sm text-midnight/65 leading-relaxed">
          <p>{t.consent}</p>
        </footer>
      </main>
    </div>
  );
}

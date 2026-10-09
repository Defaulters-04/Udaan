'use client';

import React from 'react';
import { useSessionStore } from '@/store/session';
import { SiteHeader } from '@/components/Header';

export interface PageHeadingProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  className?: string;
}

export const PageHeading: React.FC<PageHeadingProps> = ({
  title,
  subtitle,
  className = '',
}) => {
  const storeLang = useSessionStore((state) => state.lang);
  const headingFontClass = storeLang === 'hi' ? 'font-hind' : 'font-bricolage';

  return (
    <div className={`mt-8 mb-8 ${className}`}>
      <h2
        className={`${headingFontClass} font-semibold text-[clamp(24px,3vw,32px)] tracking-[-0.02em] text-midnight leading-tight`}
        style={{ fontWeight: 600 }}
      >
        {title}
      </h2>
      {subtitle && (
        <p className="mt-2 font-hind text-[16.5px] leading-relaxed text-[#3E5470]">
          {subtitle}
        </p>
      )}
    </div>
  );
};

export interface PageShellProps {
  width: 'narrow' | 'wide';
  variant?: 'standard' | 'hero';
  tagline?: string;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  footer?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export const PageShell: React.FC<PageShellProps> = ({
  width,
  variant = 'standard',
  tagline,
  title,
  subtitle,
  footer,
  children,
  className = '',
}) => {
  const containerWidthClass =
    width === 'narrow' ? 'max-w-[640px]' : 'max-w-[1160px]';

  return (
    <div className="min-h-screen bg-paper text-midnight selection:bg-sky/20 flex flex-col justify-between">
      <div
        className={`w-full mx-auto px-5 sm:px-8 flex-1 flex flex-col ${containerWidthClass}`}
      >
        <SiteHeader variant={variant} tagline={tagline} />

        {title && <PageHeading title={title} subtitle={subtitle} />}

        <main className={`flex-1 flex flex-col w-full ${className}`}>
          {children}
        </main>

        {footer}
      </div>
    </div>
  );
};

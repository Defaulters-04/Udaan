'use client';

import React, { useState, useEffect, useRef, useCallback, useMemo, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useParams } from 'next/navigation';
import { motion, useReducedMotion } from 'framer-motion';
import { useSessionStore } from '@/store/session';
import { getTranslation, type Language, type Translations } from '@/lib/i18n';
import { Header } from '@/components/Header';
import {
  getCareer,
  isMockEnabled,
  isMockToken,
  ApiError,
  type CareerDetailResponse,
  type CareerRoute,
} from '@/lib/api';

// Format rupee amounts with Indian grouping (Lakh)
function formatRupees(amount: number | null | undefined, lang: Language): string {
  if (amount === null || amount === undefined) return '';
  if (amount >= 100000) {
    const lakhs = amount / 100000;
    const formatted = lakhs % 1 === 0 ? lakhs.toString() : lakhs.toFixed(1);
    const unit = lang === 'hi' ? 'लाख' : 'Lakh';
    return `₹${formatted} ${unit}`;
  }
  return `₹${amount.toLocaleString('en-IN')}`;
}

// Map canonical domain ids to natural localized names
function getDomainLabel(domain: string, lang: Language): string {
  const map: Record<string, { en: string; hi: string }> = {
    tech_engineering: { en: 'Technology & Engineering', hi: 'तकनीकी और इंजीनियरिंग' },
    medicine_healthcare: { en: 'Medicine & Healthcare', hi: 'चिकित्सा और स्वास्थ्य' },
    business_finance: { en: 'Business & Finance', hi: 'व्यापार और वित्त' },
    creative_arts_design: { en: 'Creative Arts & Design', hi: 'रचनात्मक कला और डिज़ाइन' },
    law_public_policy: { en: 'Law & Public Policy', hi: 'कानून और लोक नीति' },
    science_research: { en: 'Science & Research', hi: 'विज्ञान और अनुसंधान' },
    teaching_social_work: { en: 'Teaching & Social Work', hi: 'शिक्षण और समाज सेवा' },
  };
  const found = map[domain];
  if (found) return found[lang] ?? found.en;
  return domain.replace(/_/g, ' ');
}

// Map data gaps to plain words
function getDataGapLabel(gap: string, t: Translations): string {
  switch (gap) {
    case 'verified_route_costs':
    case 'pathway_cost':
      return t.gap_pathway_cost || t.gap_verified_route_costs;
    case 'verified_entry_salary':
    case 'salary_benchmarks':
      return t.gap_salary_benchmarks || t.gap_verified_entry_salary;
    case 'regional_hiring':
    case 'market_demand':
      return t.gap_market_demand || t.gap_regional_hiring;
    case 'exam_pattern':
      return t.gap_exam_pattern;
    default:
      return gap.replace(/_/g, ' ');
  }
}

function CareerDetailContent() {
  const router = useRouter();
  const params = useParams();
  const shouldReduceMotion = useReducedMotion();

  const idParam = typeof params?.id === 'string' ? params.id : Array.isArray(params?.id) ? params.id[0] : '';
  const careerId = decodeURIComponent(idParam);

  // Session store
  const storeRole = useSessionStore((state) => state.role);
  const storeLang = useSessionStore((state) => state.lang);
  const storeFamily = useSessionStore((state) => state.family);
  const hasHydrated = useSessionStore((state) => state.hasHydrated);

  // Component states
  const [career, setCareer] = useState<CareerDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [isWaitingPartner, setIsWaitingPartner] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Polling ref for 409 waiting state
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Rehydrate store on mount per CONTEXT.md
  useEffect(() => {
    useSessionStore.persist.rehydrate();
  }, []);

  // Sync document language
  useEffect(() => {
    document.documentElement.lang = storeLang;
  }, [storeLang]);

  const t = getTranslation(storeLang);
  const headingFontClass = storeLang === 'hi' ? 'font-hind' : 'font-bricolage';

  // Guard: if no family or token, send to /link
  useEffect(() => {
    if (!hasHydrated) return;
    if (!storeFamily || !storeFamily.code || !storeFamily.token) {
      router.replace('/link');
    }
  }, [hasHydrated, storeFamily, router]);

  // Clean polling helper
  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  // Manual retry logic
  const handleRetry = useCallback(async () => {
    if (!storeFamily?.code || !storeFamily?.token || !careerId) return;

    setLoading(true);
    setErrorMessage(null);
    setNotFound(false);

    try {
      const data = await getCareer(storeFamily.code, storeFamily.token, careerId);
      setCareer(data);
      setIsWaitingPartner(false);
      setNotFound(false);
      stopPolling();
    } catch (err) {
      if (err instanceof ApiError && (err.code === 'explorer_not_ready' || err.status === 409)) {
        setIsWaitingPartner(true);
        setCareer(null);
      } else if (err instanceof ApiError && (err.code === 'career_not_found' || err.status === 404)) {
        setNotFound(true);
        setCareer(null);
        stopPolling();
      } else {
        setIsWaitingPartner(false);
        setErrorMessage(err instanceof ApiError ? err.message : t.careerErrorDesc);
        stopPolling();
      }
    } finally {
      setLoading(false);
    }
  }, [storeFamily, careerId, stopPolling, t.careerErrorDesc]);

  // Initial load
  useEffect(() => {
    if (!hasHydrated || !storeFamily?.code || !storeFamily?.token || !careerId) return;
    let isMounted = true;

    const loadInitialData = async () => {
      try {
        const data = await getCareer(storeFamily.code, storeFamily.token, careerId);
        if (!isMounted) return;
        setCareer(data);
        setIsWaitingPartner(false);
        setNotFound(false);
        setLoading(false);
      } catch (err) {
        if (!isMounted) return;
        if (err instanceof ApiError && (err.code === 'explorer_not_ready' || err.status === 409)) {
          setIsWaitingPartner(true);
          setCareer(null);
        } else if (err instanceof ApiError && (err.code === 'career_not_found' || err.status === 404)) {
          setNotFound(true);
          setCareer(null);
        } else {
          setIsWaitingPartner(false);
          setErrorMessage(err instanceof ApiError ? err.message : t.careerErrorDesc);
        }
        setLoading(false);
      }
    };

    loadInitialData();

    return () => {
      isMounted = false;
      stopPolling();
    };
  }, [hasHydrated, storeFamily?.code, storeFamily?.token, careerId, stopPolling, t.careerErrorDesc]);

  // Poll on 409 waiting state every 3s
  useEffect(() => {
    if (!isWaitingPartner || !storeFamily?.code || !storeFamily?.token || !careerId) return;

    pollTimerRef.current = setInterval(async () => {
      try {
        const data = await getCareer(storeFamily.code, storeFamily.token, careerId);
        setCareer(data);
        setIsWaitingPartner(false);
        stopPolling();
      } catch {
        // Keep waiting
      }
    }, 3000);

    return () => {
      stopPolling();
    };
  }, [isWaitingPartner, storeFamily?.code, storeFamily?.token, careerId, stopPolling]);

  const isMock = isMockEnabled() || isMockToken(storeFamily?.token);

  // Status line helper from blocked shape
  const getStatusLine = useMemo(() => {
    if (!career) return '';
    if (!career.blocked) return t.statusWorkable;
    switch (career.blocked.cause) {
      case 'cost':
        return t.statusNeedsPlan;
      case 'academic':
        return t.statusNeedsAcademic;
      case 'no_route_data':
        return t.statusNotEnoughData;
      default:
        return t.statusNeedsPlan;
    }
  }, [career, t]);

  // Loading state
  if (!hasHydrated || (loading && !career && !isWaitingPartner && !notFound && !errorMessage)) {
    return (
      <div className="min-h-screen bg-paper flex flex-col font-hind text-midnight">
        <Header />
        <div className="flex-1 flex items-center justify-center p-6 text-sm text-midnight/60">
          <span className="inline-block animate-pulse">{t.waiting}</span>
        </div>
      </div>
    );
  }

  // 409 Explorer not ready / waiting state
  if (isWaitingPartner) {
    return (
      <div className="min-h-screen bg-paper flex flex-col font-hind text-midnight">
        <Header />
        <main
          className="flex-1 max-w-[640px] mx-auto w-full px-4 sm:px-6 py-12 flex flex-col items-center justify-center text-center space-y-4"
          aria-live="polite"
        >
          <h2 className={`text-xl font-bold text-midnight ${headingFontClass}`}>
            {t.careerWaitingTitle}
          </h2>
          <p className="text-sm text-midnight/70 max-w-md">
            {t.careerWaitingDesc}
          </p>
          <div className="pt-4 flex items-center gap-3">
            <Link
              href="/explorer"
              className="text-xs font-semibold text-ocean hover:underline py-2 px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean rounded"
            >
              ← {t.backToExplorer}
            </Link>
          </div>
        </main>
      </div>
    );
  }

  // 404 Career not found state
  if (notFound) {
    return (
      <div className="min-h-screen bg-paper flex flex-col font-hind text-midnight">
        <Header />
        <main className="flex-1 max-w-[640px] mx-auto w-full px-4 sm:px-6 py-12 flex flex-col items-center justify-center text-center space-y-4">
          <h2 className={`text-xl font-bold text-midnight ${headingFontClass}`}>
            {t.careerNotFound}
          </h2>
          <p className="text-sm text-midnight/70 max-w-md">
            {t.careerNotFoundDesc}
          </p>
          <div className="pt-4">
            <Link
              href="/explorer"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-ocean hover:underline py-2 px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean rounded"
            >
              ← {t.backToExplorer}
            </Link>
          </div>
        </main>
      </div>
    );
  }

  // General error state (USE_MOCK=false failure)
  if (errorMessage || !career) {
    return (
      <div className="min-h-screen bg-paper flex flex-col font-hind text-midnight">
        <Header />
        <main className="flex-1 max-w-[640px] mx-auto w-full px-4 sm:px-6 py-12 flex flex-col items-center justify-center text-center space-y-4">
          <h2 className={`text-xl font-bold text-midnight ${headingFontClass}`}>
            {t.careerErrorTitle}
          </h2>
          <p className="text-sm text-midnight/70 max-w-md">
            {errorMessage || t.careerErrorDesc}
          </p>
          <div className="pt-4 flex items-center gap-4">
            <button
              type="button"
              onClick={() => handleRetry()}
              className="text-xs font-semibold text-white bg-ocean hover:bg-ocean/90 py-2 px-4 rounded-lg cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean"
            >
              {t.continue}
            </button>
            <Link
              href="/explorer"
              className="text-xs font-semibold text-ocean hover:underline py-2 px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean rounded"
            >
              ← {t.backToExplorer}
            </Link>
          </div>
        </main>
      </div>
    );
  }

  // Main Career Details Screen
  return (
    <div className="min-h-screen bg-paper flex flex-col font-hind text-midnight antialiased">
      <Header />

      <motion.main
        initial={shouldReduceMotion ? false : { opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="flex-1 max-w-[640px] mx-auto w-full px-4 sm:px-6 py-6 sm:py-8 space-y-7"
      >
        {/* Top Navigation & Mock Mode Switcher */}
        <div className="flex items-center justify-between gap-3 text-xs">
          <Link
            href="/explorer"
            className="inline-flex items-center gap-1.5 font-semibold text-ocean hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean rounded py-0.5"
          >
            ← {t.backToExplorer}
          </Link>

          {isMock && (
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-ocean/80 bg-cloud px-2 py-0.5 rounded">
                {t.demoDataLabel}
              </span>
              <span className="text-[11px] text-midnight/50">
                {career.id === 'sparse' ? (
                  <Link
                    href="/career/software_engineer"
                    className="text-ocean hover:underline"
                  >
                    {t.demoToggleFull}
                  </Link>
                ) : (
                  <Link
                    href="/career/sparse"
                    className="text-ocean hover:underline"
                  >
                    {t.demoToggleSparse}
                  </Link>
                )}
              </span>
            </div>
          )}
        </div>

        {/* 1. Heading & Key Metrics */}
        <section className="space-y-4">
          <div>
            <span className="text-xs font-medium text-midnight/60 block capitalize">
              {getDomainLabel(career.domain, storeLang)}
            </span>
            <h1 className={`text-2xl sm:text-3xl font-bold text-midnight leading-tight ${headingFontClass}`}>
              {career.name[storeLang] ?? career.name.en}
            </h1>
            <p className="text-sm font-semibold text-ocean mt-1">
              {getStatusLine}
            </p>
          </div>

          {/* Plain labeled numbers (hide any that are null) */}
          <div className="flex flex-wrap items-baseline gap-x-6 gap-y-3 pt-2 text-midnight">
            {career.fit !== null && (
              <div>
                <span className="text-xs text-midnight/60 block">{t.careerFitLabel}</span>
                <span className="text-lg font-bold font-mono text-midnight">
                  {Math.round(career.fit)}%
                </span>
              </div>
            )}

            {career.viability !== null && (
              <div>
                <span className="text-xs text-midnight/60 block">{t.careerViabilityLabel}</span>
                <span className="text-lg font-bold font-mono text-midnight">
                  {Math.round(career.viability)}%
                </span>
              </div>
            )}

            {career.years_to_income !== null && (
              <div>
                <span className="text-xs text-midnight/60 block">{t.careerYearsToIncomeLabel}</span>
                <span className="text-lg font-bold font-mono text-midnight">
                  {career.years_to_income}{' '}
                  <span className="text-xs font-normal text-midnight/70">
                    {storeLang === 'hi' ? 'वर्ष' : 'yrs'}
                  </span>
                </span>
              </div>
            )}

            {career.conflict !== null && (
              <div>
                <span className="text-xs text-midnight/60 block">{t.careerConflictLabel}</span>
                <span className="text-lg font-bold font-mono text-midnight">
                  {Math.round(career.conflict)}%
                </span>
              </div>
            )}
          </div>
        </section>

        {/* 2. Routes */}
        <section className="border-t border-cloud/90 pt-6 space-y-4">
          <h2 className={`text-base font-bold text-midnight ${headingFontClass}`}>
            {t.routesTitle}
          </h2>

          {career.routes.length === 0 ? (
            <p className="text-xs text-midnight/60 italic">
              {t.noRoutesAvailable}
            </p>
          ) : (
            <div className="space-y-4">
              {career.routes.map((route: CareerRoute) => {
                const tuition = route.cost_parts.tuition ?? 0;
                const living = route.cost_parts.living ?? 0;
                const entrance = route.cost_parts.entrance ?? 0;
                const partsTotal = tuition + living + entrance;

                const hasParts = partsTotal > 0;
                const tuitionPct = hasParts ? (tuition / partsTotal) * 100 : 0;
                const livingPct = hasParts ? (living / partsTotal) * 100 : 0;
                const entrancePct = hasParts ? (entrance / partsTotal) * 100 : 0;

                return (
                  <div key={route.id} className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-semibold text-midnight">
                            {route.label}
                          </span>
                          {route.is_best && (
                            <span className="text-[11px] font-bold text-ocean">
                              [{t.bestRouteBadge}]
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-midnight/60 flex items-center gap-2">
                          {route.years !== null && (
                            <span>
                              {route.years} {storeLang === 'hi' ? 'वर्ष' : 'yrs'}
                            </span>
                          )}
                          <span>•</span>
                          <span className="capitalize">
                            {route.cost_status === 'verified'
                              ? t.costStatusVerified
                              : t.costStatusUnverified}
                          </span>
                        </div>
                      </div>

                      {route.total_cost !== null && (
                        <span className="text-sm font-bold font-mono text-midnight whitespace-nowrap">
                          {formatRupees(route.total_cost, storeLang)}
                        </span>
                      )}
                    </div>

                    {/* Cost Parts SVG horizontal bar */}
                    {hasParts && (
                      <div className="space-y-1.5 pt-1">
                        <svg
                          width="100%"
                          height="8"
                          className="w-full rounded-full overflow-hidden bg-cloud/50"
                          aria-hidden="true"
                        >
                          {tuitionPct > 0 && (
                            <rect
                              x="0%"
                              y="0"
                              width={`${tuitionPct}%`}
                              height="8"
                              fill="#2D6FB8"
                            />
                          )}
                          {livingPct > 0 && (
                            <rect
                              x={`${tuitionPct}%`}
                              y="0"
                              width={`${livingPct}%`}
                              height="8"
                              fill="#7DBEF0"
                            />
                          )}
                          {entrancePct > 0 && (
                            <rect
                              x={`${tuitionPct + livingPct}%`}
                              y="0"
                              width={`${entrancePct}%`}
                              height="8"
                              fill="#11284A"
                            />
                          )}
                        </svg>

                        {/* Cost Legend */}
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-midnight/70">
                          {route.cost_parts.tuition !== null && (
                            <span className="inline-flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded-full bg-[#2D6FB8] inline-block" />
                              {t.tuitionCost}: {formatRupees(route.cost_parts.tuition, storeLang)}
                            </span>
                          )}
                          {route.cost_parts.living !== null && (
                            <span className="inline-flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded-full bg-[#7DBEF0] inline-block" />
                              {t.livingCost}: {formatRupees(route.cost_parts.living, storeLang)}
                            </span>
                          )}
                          {route.cost_parts.entrance !== null && (
                            <span className="inline-flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded-full bg-[#11284A] inline-block" />
                              {t.entranceCost}: {formatRupees(route.cost_parts.entrance, storeLang)}
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* 3. Entry salary (only if present) */}
        {career.entry_salary && (
          <section className="border-t border-cloud/90 pt-6 space-y-2">
            <h2 className={`text-base font-bold text-midnight ${headingFontClass}`}>
              {t.salaryTitle}
            </h2>
            <div className="text-sm text-midnight flex flex-wrap items-baseline gap-2">
              {career.entry_salary.min !== null && (
                <span>
                  {formatRupees(career.entry_salary.min, storeLang)}{' '}
                  <span className="text-xs text-midnight/60">({t.salaryMin})</span>
                </span>
              )}
              {career.entry_salary.median !== null && (
                <>
                  <span className="text-midnight/40">—</span>
                  <span className="font-semibold text-ocean">
                    {formatRupees(career.entry_salary.median, storeLang)}{' '}
                    <span className="text-xs text-midnight/60">({t.salaryMedian})</span>
                  </span>
                </>
              )}
              {career.entry_salary.max !== null && (
                <>
                  <span className="text-midnight/40">—</span>
                  <span>
                    {formatRupees(career.entry_salary.max, storeLang)}{' '}
                    <span className="text-xs text-midnight/60">({t.salaryMax})</span>
                  </span>
                </>
              )}
              <span className="text-xs text-midnight/60">/ {t.perYear}</span>
            </div>
            {career.entry_salary.source && (
              <p className="text-[11px] text-midnight/60">
                {t.sourceLabel}: {career.entry_salary.source}
              </p>
            )}
          </section>
        )}

        {/* 4. Demand (only if present) */}
        {career.demand && (
          <section className="border-t border-cloud/90 pt-6 space-y-2">
            <h2 className={`text-base font-bold text-midnight ${headingFontClass}`}>
              {t.demandTitle}
            </h2>
            <p className="text-sm font-semibold text-midnight">
              {career.demand.signal === 'positive'
                ? t.demandPositive
                : career.demand.signal === 'negative'
                ? t.demandNegative
                : t.demandNeutral}
            </p>
            {career.demand.source && (
              <p className="text-[11px] text-midnight/60">
                {t.sourceLabel}: {career.demand.source}
              </p>
            )}
          </section>
        )}

        {/* 5. Exams */}
        {career.exams && career.exams.length > 0 && (
          <section className="border-t border-cloud/90 pt-6 space-y-2">
            <h2 className={`text-base font-bold text-midnight ${headingFontClass}`}>
              {t.examsTitle}
            </h2>
            <ul className="text-sm text-midnight/90 space-y-1">
              {career.exams.map((exam, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-ocean inline-block" />
                  <span>{exam}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* 6. Scholarships */}
        <section className="border-t border-cloud/90 pt-6 space-y-2">
          <h2 className={`text-base font-bold text-midnight ${headingFontClass}`}>
            {t.scholarshipsTitle}
          </h2>
          {career.scholarships === null || career.scholarships.length === 0 ? (
            <p className="text-xs text-midnight/60 italic">
              {t.scholarshipsNotAvailable}
            </p>
          ) : (
            <ul className="text-sm text-midnight/90 space-y-1.5">
              {career.scholarships.map((s, idx) => (
                <li key={idx} className="flex items-baseline justify-between gap-2">
                  <span>{s.name}</span>
                  {s.url && (
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-semibold text-ocean hover:underline whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean rounded"
                    >
                      {t.officialLink} ↗
                    </a>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* 7. Growth areas (Student only; null for parent, so show nothing) */}
        {storeRole === 'student' && career.growth_areas && career.growth_areas.length > 0 && (
          <section className="border-t border-cloud/90 pt-6 space-y-2">
            <h2 className={`text-base font-bold text-midnight ${headingFontClass}`}>
              {t.growthAreasTitle}
            </h2>
            <p className="text-xs text-midnight/60">
              {t.growthAreasSubtitle}
            </p>
            <ul className="text-sm text-midnight/90 space-y-1.5 pt-1">
              {career.growth_areas.map((ga) => {
                const isEnglishOnly = storeLang === 'hi' && ga.text.hi === null;
                const text = ga.text[storeLang] ?? ga.text.en;
                return (
                  <li key={ga.id} className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-ocean mt-1.5 shrink-0" />
                    <span>
                      {text}
                      {isEnglishOnly && (
                        <span className="text-[10px] text-midnight/50 italic ml-1.5">
                          ({t.englishOnlyNote})
                        </span>
                      )}
                    </span>
                  </li>
                );
              })}
            </ul>
          </section>
        )}

        {/* 8. Money (Parent only; null for student, so show nothing) */}
        {storeRole === 'parent' && career.family_money && (
          <section className="border-t border-cloud/90 pt-6 space-y-2">
            <div className="flex items-baseline justify-between gap-2">
              <h2 className={`text-base font-bold text-midnight ${headingFontClass}`}>
                {t.familyMoneyTitle}
              </h2>
              <span className="text-[11px] font-medium text-ocean/80">
                {t.onlyYouSeeThis}
              </span>
            </div>

            <div className="flex flex-wrap gap-x-8 gap-y-2 pt-1 text-sm text-midnight">
              {career.family_money.loan_need !== null && (
                <div>
                  <span className="text-xs text-midnight/60 block">{t.loanNeedLabel}</span>
                  <span className="text-base font-bold font-mono text-midnight">
                    {formatRupees(career.family_money.loan_need, storeLang)}
                  </span>
                </div>
              )}

              {career.family_money.monthly_emi !== null && (
                <div>
                  <span className="text-xs text-midnight/60 block">{t.monthlyEmiLabel}</span>
                  <span className="text-base font-bold font-mono text-midnight">
                    {formatRupees(career.family_money.monthly_emi, storeLang)}{' '}
                    <span className="text-xs font-normal text-midnight/70">
                      / {t.perMonth}
                    </span>
                  </span>
                </div>
              )}
            </div>
          </section>
        )}

        {/* 9. What would help (blocked.remedies list or pathway research pending) */}
        {career.blocked && (
          <section className="border-t border-cloud/90 pt-6 space-y-2">
            <h2 className={`text-base font-bold text-midnight ${headingFontClass}`}>
              {t.whatWouldHelpTitle}
            </h2>

            {career.blocked.cause === 'no_route_data' ? (
              <p className="text-xs text-midnight/70">
                {t.pathwayResearchPending}
              </p>
            ) : career.blocked.remedies && career.blocked.remedies.length > 0 ? (
              <ul className="text-sm text-midnight/90 space-y-1.5">
                {career.blocked.remedies.map((remedy) => {
                  const isEnglishOnly = storeLang === 'hi' && remedy.text.hi === null;
                  const text = remedy.text[storeLang] ?? remedy.text.en;
                  return (
                    <li key={remedy.id} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-ocean mt-1.5 shrink-0" />
                      <span>
                        {text}
                        {isEnglishOnly && (
                          <span className="text-[10px] text-midnight/50 italic ml-1.5">
                            ({t.englishOnlyNote})
                          </span>
                        )}
                      </span>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="text-xs text-midnight/60 italic">
                {t.neutralRemedyLine}
              </p>
            )}
          </section>
        )}

        {/* 10. Footnote (Data gaps) */}
        {career.data_gaps && career.data_gaps.length > 0 && (
          <section className="border-t border-cloud/90 pt-4 text-[11px] text-midnight/60">
            <p>
              {t.dataGapsFootnote.replace(
                '{gaps}',
                career.data_gaps.map((g) => getDataGapLabel(g, t)).join(', ')
              )}
            </p>
          </section>
        )}
      </motion.main>
    </div>
  );
}

export default function CareerDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-paper flex items-center justify-center font-hind text-midnight/60 text-sm">
          <div className="w-6 h-6 rounded-full border-2 border-cloud border-t-ocean animate-spin" />
        </div>
      }
    >
      <CareerDetailContent />
    </Suspense>
  );
}

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

  // Status badge styling
  const statusBadgeConfig = useMemo(() => {
    if (!career) {
      return { bg: 'bg-cloud/60', text: 'text-midnight/80', border: 'border-cloud', dot: 'bg-midnight/40' };
    }
    if (!career.blocked) {
      return { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', dot: 'bg-emerald-500' };
    }
    switch (career.blocked.cause) {
      case 'cost':
        return { bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-200', dot: 'bg-amber-500' };
      case 'academic':
        return { bg: 'bg-sky-50', text: 'text-sky-800', border: 'border-sky-200', dot: 'bg-sky-500' };
      case 'no_route_data':
        return { bg: 'bg-purple-50', text: 'text-purple-800', border: 'border-purple-200', dot: 'bg-purple-500' };
      default:
        return { bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-200', dot: 'bg-amber-500' };
    }
  }, [career]);

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
        initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 sm:py-10 space-y-8"
      >
        {/* Top Breadcrumb & Control Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          <Link
            href="/explorer"
            className="inline-flex items-center gap-1.5 font-semibold text-ocean bg-white border border-cloud px-3 py-1.5 rounded-xl hover:border-ocean hover:shadow-sm transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean"
          >
            ← {t.backToExplorer}
          </Link>

          <div className="flex items-center gap-2.5">
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-white border border-cloud text-midnight/80 shadow-xs">
              {storeRole === 'student'
                ? `🎓 ${storeLang === 'hi' ? 'विद्यार्थी दृष्टिकोण' : 'Student Perspective'}`
                : `👨‍👩‍👧 ${storeLang === 'hi' ? 'अभिभावक दृष्टिकोण' : 'Parent Perspective'}`}
            </span>

            {isMock && (
              <div className="flex items-center gap-2 bg-white border border-cloud px-3 py-1 rounded-full shadow-xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-ocean">
                  {t.demoDataLabel}
                </span>
                <span className="text-midnight/30">•</span>
                <span className="text-[11px]">
                  {career.id === 'sparse' ? (
                    <Link
                      href="/career/software_engineer"
                      className="text-ocean hover:underline font-medium"
                    >
                      {t.demoToggleFull}
                    </Link>
                  ) : (
                    <Link
                      href="/career/sparse"
                      className="text-ocean hover:underline font-medium"
                    >
                      {t.demoToggleSparse}
                    </Link>
                  )}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* 1. Hero Dashboard Banner & KPI Deck */}
        <div className="bg-gradient-to-br from-white via-white to-sky/15 border border-cloud/90 rounded-3xl p-6 sm:p-8 lg:p-10 shadow-sm relative overflow-hidden space-y-6 sm:space-y-8">
          {/* Subtle decorative glow */}
          <div className="absolute top-0 right-0 w-96 h-96 bg-ocean/5 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

          {/* Heading and Meta Row */}
          <div className="space-y-3 relative z-10">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-ocean/10 text-ocean border border-ocean/20 capitalize">
                {getDomainLabel(career.domain, storeLang)}
              </span>

              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${statusBadgeConfig.bg} ${statusBadgeConfig.text} ${statusBadgeConfig.border}`}
              >
                <span className={`w-2 h-2 rounded-full ${statusBadgeConfig.dot} animate-pulse`} />
                {getStatusLine}
              </span>
            </div>

            <h1
              className={`text-3xl sm:text-4xl lg:text-5xl font-extrabold text-midnight tracking-tight leading-tight ${headingFontClass}`}
            >
              {career.name[storeLang] ?? career.name.en}
            </h1>

            <p className="text-sm sm:text-base text-midnight/70 font-medium max-w-3xl leading-relaxed">
              {career.blocked === null
                ? storeLang === 'hi'
                  ? 'यह करियर आपके परिवार के बजट और योग्यता दोनों के अनुकूल है।'
                  : 'This career is financially and academically viable for your family profile.'
                : career.blocked.cause === 'cost'
                ? storeLang === 'hi'
                  ? 'इस करियर के लिए वित्तीय योजना और छात्रवृत्ति सहायता की आवश्यकता हो सकती है।'
                  : 'This career requires an education loan or scholarship plan to bridge the budget gap.'
                : career.blocked.cause === 'academic'
                ? storeLang === 'hi'
                  ? 'इस करियर के लिए विशेष विषय या प्रवेश परीक्षा की तैयारी आवश्यक है।'
                  : 'This career requires specific academic prerequisites or entrance examination preparation.'
                : storeLang === 'hi'
                  ? 'इस करियर के सत्यापित शुल्क और मार्ग के आंकड़े एकत्रित किए जा रहे हैं।'
                  : 'Verified route tuition and institutional data is currently being benchmarked.'}
            </p>
          </div>

          {/* KPI Stat Cards Deck (Balanced 4 to 5 cards) */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 sm:gap-4 pt-2 relative z-10">
            {/* KPI 1: Fit */}
            {career.fit !== null && (
              <div className="bg-white/95 backdrop-blur-sm border border-cloud rounded-2xl p-4 sm:p-5 space-y-2 shadow-xs hover:border-ocean/30 transition-all">
                <span className="text-xs font-semibold text-midnight/60 block">
                  {t.careerFitLabel}
                </span>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl sm:text-3xl font-extrabold font-mono text-ocean">
                    {Math.round(career.fit)}%
                  </span>
                </div>
                <div className="w-full h-1.5 bg-cloud/70 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-ocean rounded-full transition-all duration-500"
                    style={{ width: `${career.fit}%` }}
                  />
                </div>
                <span className="text-[11px] text-midnight/60 block">
                  {storeLang === 'hi' ? 'रुचि और क्षमता मेल' : 'Aptitude & interest match'}
                </span>
              </div>
            )}

            {/* KPI 2: Viability */}
            {career.viability !== null && (
              <div className="bg-white/95 backdrop-blur-sm border border-cloud rounded-2xl p-4 sm:p-5 space-y-2 shadow-xs hover:border-midnight/30 transition-all">
                <span className="text-xs font-semibold text-midnight/60 block">
                  {t.careerViabilityLabel}
                </span>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl sm:text-3xl font-extrabold font-mono text-midnight">
                    {Math.round(career.viability)}%
                  </span>
                </div>
                <div className="w-full h-1.5 bg-cloud/70 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-midnight rounded-full transition-all duration-500"
                    style={{ width: `${career.viability}%` }}
                  />
                </div>
                <span className="text-[11px] text-midnight/60 block">
                  {storeLang === 'hi' ? 'बजट और शुल्क अनुकूलता' : 'Budget & route feasibility'}
                </span>
              </div>
            )}

            {/* KPI 3: Years to Income */}
            {career.years_to_income !== null && (
              <div className="bg-white/95 backdrop-blur-sm border border-cloud rounded-2xl p-4 sm:p-5 space-y-2 shadow-xs hover:border-ocean/30 transition-all">
                <span className="text-xs font-semibold text-midnight/60 block">
                  {t.careerYearsToIncomeLabel}
                </span>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-2xl sm:text-3xl font-extrabold font-mono text-midnight">
                    {career.years_to_income}
                  </span>
                  <span className="text-xs font-semibold text-midnight/70">
                    {storeLang === 'hi' ? 'वर्ष' : 'yrs'}
                  </span>
                </div>
                <div className="w-full h-1.5 bg-cloud/70 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-sky rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(100, Math.max(10, (career.years_to_income / 8) * 100))}%`,
                    }}
                  />
                </div>
                <span className="text-[11px] text-midnight/60 block">
                  {storeLang === 'hi' ? 'डिग्री और प्रशिक्षण अवधि' : 'Study & training duration'}
                </span>
              </div>
            )}

            {/* KPI 4: Conflict / Alignment */}
            {career.conflict !== null && (
              <div className="bg-white/95 backdrop-blur-sm border border-cloud rounded-2xl p-4 sm:p-5 space-y-2 shadow-xs hover:border-ocean/30 transition-all">
                <span className="text-xs font-semibold text-midnight/60 block">
                  {t.careerConflictLabel}
                </span>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl sm:text-3xl font-extrabold font-mono text-midnight">
                    {Math.round(career.conflict)}%
                  </span>
                </div>
                <div className="w-full h-1.5 bg-cloud/70 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-amber-500 rounded-full transition-all duration-500"
                    style={{ width: `${career.conflict}%` }}
                  />
                </div>
                <span className="text-[11px] text-midnight/60 block truncate">
                  {career.conflict <= 25
                    ? storeLang === 'hi'
                      ? 'उच्च पारिवारिक सहमति'
                      : 'Strong family harmony'
                    : career.conflict <= 50
                    ? storeLang === 'hi'
                      ? 'सामान्य चर्चा आवश्यक'
                      : 'Moderate discussion'
                    : storeLang === 'hi'
                    ? 'प्राथमिकताओं में अंतर'
                    : 'Active negotiation'}
                </span>
              </div>
            )}

            {/* KPI 5: Median Starting Salary (if available) */}
            {career.entry_salary?.median ? (
              <div className="bg-white/95 backdrop-blur-sm border border-cloud rounded-2xl p-4 sm:p-5 space-y-2 shadow-xs col-span-2 md:col-span-4 lg:col-span-1 hover:border-ocean/30 transition-all">
                <span className="text-xs font-semibold text-midnight/60 block">
                  {storeLang === 'hi' ? 'प्रारंभिक वेतन (मध्यमान)' : 'Starting Salary (Median)'}
                </span>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl sm:text-3xl font-extrabold font-mono text-ocean">
                    {formatRupees(career.entry_salary.median, storeLang)}
                  </span>
                </div>
                <span className="text-[11px] text-midnight/60 block">
                  / {t.perYear} ({career.entry_salary.source || 'Industry avg'})
                </span>
              </div>
            ) : null}
          </div>
        </div>

        {/* 2. Main Dashboard Multi-Column Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* LEFT MAIN COLUMN: Pathways, Action Plan, Exams, Growth Areas (8 Cols) */}
          <div className="lg:col-span-8 space-y-8">
            {/* Section A: Education Pathways (Routes) */}
            <section className="bg-white border border-cloud/90 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cloud/60 pb-4">
                <div className="flex items-center gap-3">
                  <span className="w-9 h-9 rounded-xl bg-ocean/10 text-ocean flex items-center justify-center text-lg font-bold">
                    🎓
                  </span>
                  <div>
                    <h2 className={`text-xl font-bold text-midnight ${headingFontClass}`}>
                      {t.routesTitle}
                    </h2>
                    <span className="text-xs text-midnight/60">
                      {storeLang === 'hi'
                        ? 'विभिन्न कॉलेजों और प्रवेश मार्गों के आधार पर कुल लागत व समय'
                        : 'Duration, verified tuition, and living costs across routes'}
                    </span>
                  </div>
                </div>

                <span className="px-3 py-1 rounded-full text-xs font-bold bg-cloud/50 text-midnight/80 border border-cloud">
                  {career.routes.length}{' '}
                  {storeLang === 'hi' ? 'रास्ते उपलब्ध' : 'Pathways Available'}
                </span>
              </div>

              {career.routes.length === 0 ? (
                <div className="p-8 text-center bg-paper/60 border border-cloud rounded-2xl space-y-2">
                  <p className="text-sm text-midnight/70 font-medium">
                    {t.noRoutesAvailable}
                  </p>
                  <p className="text-xs text-midnight/50">
                    {t.pathwayResearchPending}
                  </p>
                </div>
              ) : (
                <div className="space-y-5">
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
                      <div
                        key={route.id}
                        className={`border rounded-2xl p-5 sm:p-6 transition-all space-y-4 ${
                          route.is_best
                            ? 'bg-ocean/[0.03] border-ocean/40 shadow-xs'
                            : 'bg-paper/40 border-cloud/90 hover:border-ocean/30'
                        }`}
                      >
                        {/* Route Title & Cost Header */}
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <h3 className="text-base sm:text-lg font-bold text-midnight">
                                {route.label}
                              </h3>
                              {route.is_best && (
                                <span className="inline-flex items-center gap-1 text-[11px] font-bold text-ocean bg-ocean/10 px-2.5 py-0.5 rounded-full border border-ocean/20">
                                  ★ {t.bestRouteBadge}
                                </span>
                              )}
                            </div>

                            <div className="flex items-center gap-2.5 text-xs text-midnight/70">
                              {route.years !== null && (
                                <span className="font-medium">
                                  ⏱️ {route.years} {storeLang === 'hi' ? 'वर्ष' : 'yrs'}
                                </span>
                              )}
                              <span>•</span>
                              <span
                                className={`font-semibold ${
                                  route.cost_status === 'verified'
                                    ? 'text-emerald-700'
                                    : 'text-midnight/60'
                                }`}
                              >
                                {route.cost_status === 'verified'
                                  ? `✓ ${t.costStatusVerified}`
                                  : `~ ${t.costStatusUnverified}`}
                              </span>
                            </div>
                          </div>

                          {route.total_cost !== null && (
                            <div className="text-right">
                              <span className="text-xs text-midnight/60 block">
                                {storeLang === 'hi' ? 'अनुमानित कुल खर्च' : 'Estimated Total Cost'}
                              </span>
                              <span className="text-xl sm:text-2xl font-black font-mono text-midnight">
                                {formatRupees(route.total_cost, storeLang)}
                              </span>
                            </div>
                          )}
                        </div>

                        {/* Segmented Horizontal Bar */}
                        {hasParts && (
                          <div className="space-y-2 pt-1">
                            <div className="h-2.5 w-full bg-cloud/60 rounded-full overflow-hidden flex">
                              {tuitionPct > 0 && (
                                <div
                                  style={{ width: `${tuitionPct}%` }}
                                  className="h-full bg-[#2D6FB8] transition-all duration-300"
                                  title={`${t.tuitionCost}: ${formatRupees(route.cost_parts.tuition, storeLang)}`}
                                />
                              )}
                              {livingPct > 0 && (
                                <div
                                  style={{ width: `${livingPct}%` }}
                                  className="h-full bg-[#7DBEF0] transition-all duration-300"
                                  title={`${t.livingCost}: ${formatRupees(route.cost_parts.living, storeLang)}`}
                                />
                              )}
                              {entrancePct > 0 && (
                                <div
                                  style={{ width: `${entrancePct}%` }}
                                  className="h-full bg-[#11284A] transition-all duration-300"
                                  title={`${t.entranceCost}: ${formatRupees(route.cost_parts.entrance, storeLang)}`}
                                />
                              )}
                            </div>

                            {/* Legend Details */}
                            <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-midnight/80 pt-0.5">
                              {route.cost_parts.tuition !== null && (
                                <span className="inline-flex items-center gap-1.5">
                                  <span className="w-2.5 h-2.5 rounded-full bg-[#2D6FB8] inline-block shrink-0" />
                                  <span className="text-midnight/70">{t.tuitionCost}:</span>
                                  <span className="font-mono font-bold text-midnight">
                                    {formatRupees(route.cost_parts.tuition, storeLang)}
                                  </span>
                                </span>
                              )}
                              {route.cost_parts.living !== null && (
                                <span className="inline-flex items-center gap-1.5">
                                  <span className="w-2.5 h-2.5 rounded-full bg-[#7DBEF0] inline-block shrink-0" />
                                  <span className="text-midnight/70">{t.livingCost}:</span>
                                  <span className="font-mono font-bold text-midnight">
                                    {formatRupees(route.cost_parts.living, storeLang)}
                                  </span>
                                </span>
                              )}
                              {route.cost_parts.entrance !== null && (
                                <span className="inline-flex items-center gap-1.5">
                                  <span className="w-2.5 h-2.5 rounded-full bg-[#11284A] inline-block shrink-0" />
                                  <span className="text-midnight/70">{t.entranceCost}:</span>
                                  <span className="font-mono font-bold text-midnight">
                                    {formatRupees(route.cost_parts.entrance, storeLang)}
                                  </span>
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

            {/* Section B: What Would Help / Remedial Roadmap (Shown when career is blocked) */}
            {career.blocked && (
              <section className="bg-gradient-to-br from-amber-50/50 via-white to-ocean/5 border border-amber-200/90 rounded-3xl p-6 sm:p-8 shadow-sm space-y-5">
                <div className="flex items-center gap-3 border-b border-amber-200/60 pb-4">
                  <span className="w-9 h-9 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center text-lg font-bold">
                    💡
                  </span>
                  <div>
                    <h2 className={`text-xl font-bold text-midnight ${headingFontClass}`}>
                      {t.whatWouldHelpTitle}
                    </h2>
                    <p className="text-xs text-midnight/70">
                      {storeLang === 'hi'
                        ? 'इस करियर को संभव बनाने के लिए आवश्यक कदम और रणनीतियाँ'
                        : 'Key steps and financial bridges to make this pathway feasible'}
                    </p>
                  </div>
                </div>

                {career.blocked.cause === 'no_route_data' ? (
                  <p className="text-sm text-midnight/75 leading-relaxed bg-white/80 p-4 rounded-xl border border-cloud">
                    {t.pathwayResearchPending}
                  </p>
                ) : career.blocked.remedies && career.blocked.remedies.length > 0 ? (
                  <div className="space-y-3">
                    {career.blocked.remedies.map((remedy, idx) => {
                      const isEnglishOnly = storeLang === 'hi' && remedy.text.hi === null;
                      const text = remedy.text[storeLang] ?? remedy.text.en;
                      return (
                        <div
                          key={remedy.id}
                          className="bg-white/95 border border-amber-200/60 rounded-2xl p-4 flex items-start gap-3.5 shadow-xs"
                        >
                          <span className="w-7 h-7 rounded-lg bg-amber-100 text-amber-900 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                            {idx + 1}
                          </span>
                          <div className="space-y-1">
                            <p className="text-sm font-semibold text-midnight leading-relaxed">
                              {text}
                            </p>
                            {isEnglishOnly && (
                              <span className="text-[10px] text-midnight/50 italic block">
                                ({t.englishOnlyNote})
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-midnight/60 italic bg-white/80 p-4 rounded-xl border border-cloud">
                    {t.neutralRemedyLine}
                  </p>
                )}
              </section>
            )}

            {/* Section C: Entrance Examinations */}
            {career.exams && career.exams.length > 0 && (
              <section className="bg-white border border-cloud/90 rounded-3xl p-6 sm:p-8 shadow-sm space-y-5">
                <div className="flex items-center justify-between border-b border-cloud/60 pb-4">
                  <div className="flex items-center gap-3">
                    <span className="w-9 h-9 rounded-xl bg-ocean/10 text-ocean flex items-center justify-center text-lg font-bold">
                      📝
                    </span>
                    <div>
                      <h2 className={`text-xl font-bold text-midnight ${headingFontClass}`}>
                        {t.examsTitle}
                      </h2>
                      <span className="text-xs text-midnight/60">
                        {storeLang === 'hi'
                          ? 'इस करियर में प्रवेश के लिए प्रमुख राष्ट्रीय व राज्य स्तरीय परीक्षाएं'
                          : 'Major qualifying exams and competitive entrance tests'}
                      </span>
                    </div>
                  </div>

                  <span className="px-3 py-1 rounded-full text-xs font-semibold bg-ocean/10 text-ocean border border-ocean/20">
                    {career.exams.length} {storeLang === 'hi' ? 'परीक्षाएं' : 'Exams'}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {career.exams.map((exam, i) => (
                    <div
                      key={i}
                      className="p-4 rounded-2xl bg-paper/60 border border-cloud hover:border-ocean/40 transition-colors flex items-center gap-3"
                    >
                      <span className="w-8 h-8 rounded-xl bg-white border border-cloud flex items-center justify-center text-xs font-bold text-ocean shrink-0 shadow-xs">
                        {i + 1}
                      </span>
                      <div className="min-w-0">
                        <span className="text-sm font-bold text-midnight block truncate">
                          {exam}
                        </span>
                        <span className="text-[11px] text-midnight/50 block">
                          {storeLang === 'hi' ? 'प्रवेश परीक्षा' : 'Entrance Examination'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Section D: Student Growth Areas (Student View Only) */}
            {storeRole === 'student' && career.growth_areas && career.growth_areas.length > 0 && (
              <section className="bg-white border border-cloud/90 rounded-3xl p-6 sm:p-8 shadow-sm space-y-5">
                <div className="flex items-center gap-3 border-b border-cloud/60 pb-4">
                  <span className="w-9 h-9 rounded-xl bg-ocean/10 text-ocean flex items-center justify-center text-lg font-bold">
                    🚀
                  </span>
                  <div>
                    <h2 className={`text-xl font-bold text-midnight ${headingFontClass}`}>
                      {t.growthAreasTitle}
                    </h2>
                    <p className="text-xs text-midnight/60">
                      {t.growthAreasSubtitle}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-3">
                  {career.growth_areas.map((ga) => {
                    const isEnglishOnly = storeLang === 'hi' && ga.text.hi === null;
                    const text = ga.text[storeLang] ?? ga.text.en;
                    return (
                      <div
                        key={ga.id}
                        className="p-4 rounded-2xl bg-paper/50 border border-cloud flex items-start gap-3 hover:border-ocean/30 transition-all"
                      >
                        <span className="w-6 h-6 rounded-full bg-ocean text-white font-bold text-xs flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
                          ✓
                        </span>
                        <div className="space-y-0.5">
                          <p className="text-sm font-semibold text-midnight leading-relaxed">
                            {text}
                          </p>
                          {isEnglishOnly && (
                            <span className="text-[10px] text-midnight/50 italic block">
                              ({t.englishOnlyNote})
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}
          </div>

          {/* RIGHT SIDEBAR COLUMN: Salary Range, Market Demand, Parent Finance, Scholarships, Gaps (4 Cols) */}
          <div className="lg:col-span-4 space-y-8">
            {/* Widget 1: Market & Salary Benchmarks */}
            <div className="bg-white border border-cloud/90 rounded-3xl p-6 sm:p-7 shadow-sm space-y-6">
              {/* Salary Section */}
              {career.entry_salary && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2.5 border-b border-cloud/60 pb-3">
                    <span className="text-base">💼</span>
                    <h3 className={`text-base font-bold text-midnight ${headingFontClass}`}>
                      {t.salaryTitle}
                    </h3>
                  </div>

                  {/* Visual Range Display */}
                  <div className="bg-paper/70 p-4 rounded-2xl border border-cloud/80 space-y-3">
                    <div className="flex items-baseline justify-between">
                      <span className="text-xs font-semibold text-midnight/60">
                        {t.salaryMedian}
                      </span>
                      <span className="text-xl font-extrabold font-mono text-ocean">
                        {career.entry_salary.median !== null
                          ? formatRupees(career.entry_salary.median, storeLang)
                          : '—'}
                      </span>
                    </div>

                    {/* Gradient Min-Max Indicator Bar */}
                    <div className="space-y-1.5">
                      <div className="h-2 w-full bg-cloud rounded-full overflow-hidden relative">
                        <div className="h-full bg-gradient-to-r from-sky via-ocean to-midnight rounded-full" />
                      </div>
                      <div className="flex justify-between text-[11px] font-mono text-midnight/70 font-semibold">
                        <span>
                          {career.entry_salary.min !== null
                            ? formatRupees(career.entry_salary.min, storeLang)
                            : ''}{' '}
                          <span className="font-normal text-midnight/50">({t.salaryMin})</span>
                        </span>
                        <span>
                          {career.entry_salary.max !== null
                            ? formatRupees(career.entry_salary.max, storeLang)
                            : ''}{' '}
                          <span className="font-normal text-midnight/50">({t.salaryMax})</span>
                        </span>
                      </div>
                    </div>

                    <span className="text-[11px] text-midnight/50 block">
                      / {t.perYear} • {t.sourceLabel}: {career.entry_salary.source || 'Industry database'}
                    </span>
                  </div>
                </div>
              )}

              {/* Demand Signal Section */}
              {career.demand && (
                <div className="space-y-3 pt-2 border-t border-cloud/60">
                  <div className="flex items-center gap-2.5">
                    <span className="text-base">📈</span>
                    <h3 className={`text-base font-bold text-midnight ${headingFontClass}`}>
                      {t.demandTitle}
                    </h3>
                  </div>

                  <div className="p-4 rounded-2xl bg-paper/60 border border-cloud space-y-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-2.5 h-2.5 rounded-full ${
                          career.demand.signal === 'positive'
                            ? 'bg-emerald-500 animate-pulse'
                            : career.demand.signal === 'negative'
                            ? 'bg-rose-500'
                            : 'bg-cloud'
                        }`}
                      />
                      <span className="text-sm font-bold text-midnight">
                        {career.demand.signal === 'positive'
                          ? t.demandPositive
                          : career.demand.signal === 'negative'
                          ? t.demandNegative
                          : t.demandNeutral}
                      </span>
                    </div>

                    {career.demand.source && (
                      <p className="text-[11px] text-midnight/60">
                        {t.sourceLabel}: {career.demand.source}
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Widget 2: Family Financial Plan (Parent View Only) */}
            {storeRole === 'parent' && career.family_money && (
              <div className="bg-gradient-to-br from-[#0F223D] via-[#11284A] to-[#183968] text-white border border-ocean/30 rounded-3xl p-6 sm:p-7 shadow-lg space-y-5">
                <div className="flex items-center justify-between gap-2 border-b border-white/10 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-base">💰</span>
                    <h3 className={`text-base font-bold text-white ${headingFontClass}`}>
                      {t.familyMoneyTitle}
                    </h3>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-white/10 text-sky border border-white/15">
                    🔒 {t.onlyYouSeeThis}
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-3.5">
                  {career.family_money.loan_need !== null && (
                    <div className="bg-white/10 backdrop-blur-xs p-4 rounded-2xl border border-white/10 space-y-1">
                      <span className="text-xs text-white/70 block">
                        {t.loanNeedLabel}
                      </span>
                      <span className="text-2xl font-black font-mono text-sky block">
                        {formatRupees(career.family_money.loan_need, storeLang)}
                      </span>
                    </div>
                  )}

                  {career.family_money.monthly_emi !== null && (
                    <div className="bg-white/10 backdrop-blur-xs p-4 rounded-2xl border border-white/10 space-y-1">
                      <span className="text-xs text-white/70 block">
                        {t.monthlyEmiLabel}
                      </span>
                      <span className="text-2xl font-black font-mono text-white block">
                        {formatRupees(career.family_money.monthly_emi, storeLang)}{' '}
                        <span className="text-xs font-normal text-white/60">/ {t.perMonth}</span>
                      </span>
                    </div>
                  )}
                </div>

                <p className="text-[11px] text-white/60 leading-relaxed">
                  {storeLang === 'hi'
                    ? 'यह आकलन आपके द्वारा चुने गए बजट और शिक्षा ऋण वरीयताओं पर आधारित है।'
                    : 'Estimated financing scenario calculated from your intake budget tolerance.'}
                </p>
              </div>
            )}

            {/* Widget 3: Scholarships & Aid Opportunities */}
            <div className="bg-white border border-cloud/90 rounded-3xl p-6 sm:p-7 shadow-sm space-y-4">
              <div className="flex items-center gap-2.5 border-b border-cloud/60 pb-3">
                <span className="text-base">🎁</span>
                <h3 className={`text-base font-bold text-midnight ${headingFontClass}`}>
                  {t.scholarshipsTitle}
                </h3>
              </div>

              {career.scholarships === null || career.scholarships.length === 0 ? (
                <p className="text-xs text-midnight/60 italic p-3 bg-paper/60 rounded-xl border border-cloud">
                  {t.scholarshipsNotAvailable}
                </p>
              ) : (
                <div className="space-y-2.5">
                  {career.scholarships.map((s, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-2xl bg-paper/60 border border-cloud hover:border-ocean/40 transition-all flex items-center justify-between gap-2"
                    >
                      <span className="text-xs font-semibold text-midnight truncate">
                        {s.name}
                      </span>
                      {s.url && (
                        <a
                          href={s.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[11px] font-bold text-ocean hover:underline whitespace-nowrap px-2.5 py-1 rounded-lg bg-white border border-ocean/30 hover:bg-ocean hover:text-white transition-colors shrink-0"
                        >
                          {t.officialLink} ↗
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Widget 4: Data Quality & Gaps Transparency */}
            {career.data_gaps && career.data_gaps.length > 0 && (
              <div className="bg-paper/80 border border-cloud rounded-3xl p-5 space-y-2 text-xs text-midnight/70">
                <div className="flex items-center gap-1.5 font-bold text-midnight text-xs">
                  <span>ℹ️</span>
                  <span>{storeLang === 'hi' ? 'डेटा पारदर्शिता' : 'Data Transparency'}</span>
                </div>
                <p className="text-[11px] leading-relaxed text-midnight/60">
                  {t.dataGapsFootnote.replace(
                    '{gaps}',
                    career.data_gaps.map((g) => getDataGapLabel(g, t)).join(', ')
                  )}
                </p>
              </div>
            )}
          </div>
        </div>
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

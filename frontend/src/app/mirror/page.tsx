'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, useReducedMotion } from 'framer-motion';
import { useSessionStore } from '@/store/session';
import { getTranslation } from '@/lib/i18n';
import { Header } from '@/components/Header';
import {
  getMirror,
  getStatus,
  ApiError,
  type MirrorResponse,
  type MirrorScaleDimension,
  type MirrorPicksDimension,
  type MirrorDimension,
} from '@/lib/api';

export default function FamilyMirrorPage() {
  const router = useRouter();
  const shouldReduceMotion = useReducedMotion();

  // Session Store
  const storeRole = useSessionStore((state) => state.role);
  const storeName = useSessionStore((state) => state.name);
  const storeLang = useSessionStore((state) => state.lang);
  const storeFamily = useSessionStore((state) => state.family);
  const hasHydrated = useSessionStore((state) => state.hasHydrated);

  // Component State only (NEVER persisted to store or storage per contract)
  const [mirrorData, setMirrorData] = useState<MirrorResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [isWaitingPartner, setIsWaitingPartner] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Polling ref
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isPollingRef = useRef(false);

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

  // Guard: if no family or token, send to /
  useEffect(() => {
    if (!hasHydrated) return;
    if (!storeFamily || !storeFamily.code || !storeFamily.token) {
      router.replace('/');
    }
  }, [hasHydrated, storeFamily, router]);

  // Clean helper for polling
  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    isPollingRef.current = false;
  }, []);

  // Fetch Mirror logic for manual retry
  const fetchMirror = useCallback(async () => {
    if (!storeFamily || !storeFamily.code || !storeFamily.token) return;

    setLoading(true);
    setErrorMessage(null);

    try {
      const data = await getMirror(storeFamily.code, storeFamily.token);
      setMirrorData(data);
      setIsWaitingPartner(false);
      stopPolling();
    } catch (err) {
      if (err instanceof ApiError && (err.code === 'mirror_not_ready' || err.status === 409)) {
        setIsWaitingPartner(true);
        setMirrorData(null);
      } else {
        setIsWaitingPartner(false);
        setErrorMessage(
          err instanceof ApiError ? err.message : t.mirrorErrorDesc
        );
      }
    } finally {
      setLoading(false);
    }
  }, [storeFamily, stopPolling, t.mirrorErrorDesc]);

  // Initial load once hydrated and family is available
  useEffect(() => {
    if (!hasHydrated || !storeFamily?.code || !storeFamily?.token) return;

    let isMounted = true;

    const loadInitialData = async () => {
      try {
        const data = await getMirror(storeFamily.code, storeFamily.token);
        if (!isMounted) return;
        setMirrorData(data);
        setIsWaitingPartner(false);
        setLoading(false);
      } catch (err) {
        if (!isMounted) return;
        if (err instanceof ApiError && (err.code === 'mirror_not_ready' || err.status === 409)) {
          setIsWaitingPartner(true);
          setMirrorData(null);
        } else {
          setIsWaitingPartner(false);
          setErrorMessage(
            err instanceof ApiError ? err.message : t.mirrorErrorDesc
          );
        }
        setLoading(false);
      }
    };

    loadInitialData();

    return () => {
      isMounted = false;
    };
  }, [hasHydrated, storeFamily?.code, storeFamily?.token, t.mirrorErrorDesc]);

  // 409 mirror_not_ready polling: poll getStatus every 2s
  useEffect(() => {
    if (!isWaitingPartner || !storeFamily?.code || !storeFamily?.token) {
      stopPolling();
      return;
    }

    if (isPollingRef.current) return;
    isPollingRef.current = true;

    const checkBothDone = async () => {
      try {
        const status = await getStatus(storeFamily.code, storeFamily.token);
        if (status.you.done && status.partner?.done) {
          stopPolling();
          fetchMirror();
        }
      } catch {
        // Silently retry on next poll cycle
      }
    };

    pollTimerRef.current = setInterval(checkBothDone, 2000);

    return () => {
      stopPolling();
    };
  }, [isWaitingPartner, storeFamily, fetchMirror, stopPolling]);

  // Determine display names: student and parent
  const myRole = storeRole;
  const myName = storeName || (myRole === 'student' ? t.student : t.parent);
  const partnerName =
    storeFamily?.partner?.name || (myRole === 'student' ? t.parent : t.student);

  const studentName = myRole === 'student' ? myName : partnerName;
  const parentName = myRole === 'parent' ? myName : partnerName;

  const truncate = (str: string, maxLen: number = 20): string => {
    if (!str) return '';
    return str.length > maxLen ? str.slice(0, maxLen) + '…' : str;
  };

  const studentDisplayName = truncate(studentName);
  const parentDisplayName = truncate(parentName);

  // Helper for scale summary sentence
  const getScaleSummary = (dim: MirrorScaleDimension): string => {
    let templateKey: string;
    if (dim.student_step === dim.parent_step) {
      templateKey = `${dim.id}_same`;
    } else if (dim.student_step > dim.parent_step) {
      templateKey = `${dim.id}_studentHigher`;
    } else {
      templateKey = `${dim.id}_parentHigher`;
    }

    let tmpl = (t as unknown as Record<string, string>)[templateKey];
    if (!tmpl) {
      if (dim.student_step === dim.parent_step) {
        tmpl = t.scale_same;
      } else if (dim.student_step > dim.parent_step) {
        tmpl = t.scale_studentHigher;
      } else {
        tmpl = t.scale_parentHigher;
      }
    }

    return tmpl
      .replace('{student}', studentDisplayName)
      .replace('{parent}', parentDisplayName);
  };

  // Helper for picks shared domains sentence
  const getPicksSharedSentence = (dim: MirrorPicksDimension): string => {
    const shared = dim.options.filter(
      (opt) =>
        dim.student_picks.includes(opt.id) && dim.parent_picks.includes(opt.id)
    );
    if (shared.length > 0) {
      const names = shared
        .map((o) => o.label[storeLang] ?? o.label.en)
        .join(', ');
      return t.domain_shared
        .replace('{student}', studentDisplayName)
        .replace('{parent}', parentDisplayName)
        .replace('{domains}', names);
    }
    return t.domain_none;
  };

  // Helper for picks perception sentence
  const getPicksPerceptionSentence = (dim: MirrorPicksDimension): string => {
    if (!dim.parent_guess) return '';
    const guessOpt = dim.options.find((o) => o.id === dim.parent_guess);
    const guessName = guessOpt
      ? guessOpt.label[storeLang] ?? guessOpt.label.en
      : dim.parent_guess;

    if (dim.student_picks.includes(dim.parent_guess)) {
      return t.domain_guessMatch
        .replace('{parent}', parentDisplayName)
        .replace('{student}', studentDisplayName)
        .replace('{domain}', guessName);
    }

    const studentOpts = dim.options.filter((o) =>
      dim.student_picks.includes(o.id)
    );
    const studentList =
      studentOpts.length > 0
        ? studentOpts.map((o) => o.label[storeLang] ?? o.label.en).join(', ')
        : '—';

    return t.domain_guessMismatch
      .replace('{parent}', parentDisplayName)
      .replace('{domain}', guessName)
      .replace('{student}', studentDisplayName)
      .replace('{list}', studentList);
  };

  // Semicircular arc metrics (R = 75, Center = 100, 95)
  // Arc length = pi * 75 ~= 235.62
  const arcTotal = 235.62;
  const conflictIndex = mirrorData ? mirrorData.conflict_index : 0;
  const isHighConflict = mirrorData?.high_conflict ?? false;
  const clampedIndex = Math.min(100, Math.max(0, conflictIndex));
  const strokeDashoffset = arcTotal * (1 - clampedIndex / 100);

  return (
    <div className="min-h-screen bg-paper text-midnight selection:bg-sky/20 flex flex-col justify-between">
      <main className="w-full max-w-2xl mx-auto px-5 sm:px-6 pt-6 sm:pt-10 pb-16 flex-1 flex flex-col">
        {/* Header with Wordmark and Language Toggle */}
        <Header tagline={t.mirrorSubtitle} />

        {/* LOADING STATE */}
        {loading && !mirrorData && !isWaitingPartner && (
          <div className="flex-1 flex flex-col items-center justify-center py-20 text-center">
            <div className="w-8 h-8 rounded-full border-2 border-cloud border-t-ocean animate-spin mb-4" />
            <p className="text-sm text-midnight/70 font-medium">
              {t.saving ? t.saving.replace('…', '') : 'Loading'}…
            </p>
          </div>
        )}

        {/* WAITING STATE (409 mirror_not_ready) */}
        {!loading && isWaitingPartner && (
          <div
            aria-live="polite"
            className="w-full bg-white rounded-2xl p-8 sm:p-10 border border-cloud shadow-sm text-center space-y-4 my-8"
          >
            <div className="w-14 h-14 rounded-full bg-cloud flex items-center justify-center mx-auto text-ocean">
              <span className="w-4 h-4 rounded-full bg-ocean animate-pulse" />
            </div>
            <h2 className={`${headingFontClass} text-2xl font-bold text-midnight`}>
              {t.mirrorWaitingTitle.replace('{partner}', parentDisplayName)}
            </h2>
            <p className="text-base text-midnight/70 max-w-md mx-auto leading-relaxed">
              {t.mirrorWaitingDesc.replace('{partner}', parentDisplayName)}
            </p>
            <div className="flex items-center justify-center gap-2 pt-2 text-xs text-midnight/55 font-medium">
              <span className="w-2 h-2 rounded-full bg-ocean animate-pulse" />
              <span>{t.mirrorWaitingBadge}</span>
            </div>
          </div>
        )}

        {/* ERROR STATE */}
        {!loading && errorMessage && !isWaitingPartner && (
          <div
            role="alert"
            className="w-full bg-white rounded-2xl p-8 sm:p-10 border border-cloud shadow-sm text-center space-y-4 my-8"
          >
            <h2 className={`${headingFontClass} text-2xl font-bold text-midnight`}>
              {t.mirrorErrorTitle}
            </h2>
            <p className="text-base text-midnight/70 max-w-md mx-auto leading-relaxed">
              {errorMessage}
            </p>
            <div className="pt-2">
              <button
                type="button"
                onClick={fetchMirror}
                className="px-6 py-2.5 bg-ocean text-white font-semibold text-sm rounded-xl hover:bg-[#255ba0] transition-colors focus-visible:outline-2 focus-visible:outline-ocean cursor-pointer"
              >
                {t.retry}
              </button>
            </div>
          </div>
        )}

        {/* SUCCESS / MIRROR CONTENT */}
        {!loading && mirrorData && (
          <div className="space-y-10">
            {/* Title */}
            <div>
              <h2
                className={`${headingFontClass} text-2xl sm:text-3xl font-bold text-midnight`}
              >
                {t.mirrorTitle}
              </h2>
            </div>

            {/* Semicircular Meter (Conflict Gauge) */}
            <div className="bg-white rounded-2xl p-6 sm:p-8 border border-cloud shadow-sm flex flex-col items-center text-center">
              <div
                className="relative w-64 h-36 flex flex-col items-center justify-end"
                role="meter"
                aria-valuenow={conflictIndex}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={t.gaugeAria.replace(
                  '{score}',
                  conflictIndex.toString()
                )}
              >
                <svg
                  viewBox="0 0 200 110"
                  className="w-full h-full overflow-visible"
                  aria-hidden="true"
                >
                  {/* Background Track */}
                  <path
                    d="M 25 95 A 75 75 0 0 1 175 95"
                    fill="none"
                    stroke="#E3EEF8"
                    strokeWidth="12"
                    strokeLinecap="round"
                  />
                  {/* Foreground Animated Value Arc */}
                  <motion.path
                    d="M 25 95 A 75 75 0 0 1 175 95"
                    fill="none"
                    stroke={isHighConflict ? '#B45309' : '#2D6FB8'}
                    strokeWidth="12"
                    strokeLinecap="round"
                    strokeDasharray={arcTotal}
                    initial={{ strokeDashoffset: arcTotal }}
                    animate={{ strokeDashoffset }}
                    transition={{
                      duration: shouldReduceMotion ? 0 : 1.2,
                      ease: 'easeOut',
                    }}
                  />
                </svg>

                {/* Score Number in Center */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pt-8 pointer-events-none select-none">
                  <span className="font-bricolage text-4xl sm:text-5xl font-extrabold text-midnight tracking-tight">
                    {Math.round(conflictIndex * 10) / 10}
                  </span>
                  <span className="text-xs sm:text-sm font-medium text-midnight/60 mt-0.5">
                    {t.gaugeOutOf100}
                  </span>
                </div>
              </div>

              {/* Semicircular Gauge Caption */}
              <p className="mt-4 text-xs sm:text-sm text-midnight/70 max-w-sm leading-relaxed">
                {t.gaugeCaption}
              </p>
            </div>

            {/* Dimensions Rows */}
            <div className="space-y-6">
              {mirrorData.dimensions.map((dim: MirrorDimension) => {
                const dimTitle =
                  (t as unknown as Record<string, string>)[`dim_${dim.id}`] ||
                  dim.id.replace(/_/g, ' ');

                return (
                  <div
                    key={dim.id}
                    className="bg-white rounded-2xl p-5 sm:p-6 border border-cloud shadow-sm space-y-4"
                  >
                    {/* Row Header */}
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5 sm:gap-4 pb-3 border-b border-cloud/60">
                      <h3
                        className={`${headingFontClass} text-lg sm:text-xl font-bold text-midnight`}
                      >
                        {dimTitle}
                      </h3>
                      <div className="flex flex-wrap items-center gap-2 text-xs font-medium">
                        <span className="bg-cloud text-midnight px-2.5 py-1 rounded-full">
                          {t.diffPercent.replace(
                            '{n}',
                            Math.round(dim.gap * 100).toString()
                          )}
                        </span>
                        <span className="text-midnight/60">
                          {t.weightPercent.replace(
                            '{n}',
                            Math.round(dim.weight * 100).toString()
                          )}
                        </span>
                      </div>
                    </div>

                    {/* Scale Dimension */}
                    {dim.kind === 'scale' && (
                      <div className="space-y-3 pt-1">
                        <div className="space-y-2">
                          {dim.steps.map((step, idx) => {
                            const isStudent = dim.student_step === idx;
                            const isParent = dim.parent_step === idx;
                            const isBoth = isStudent && isParent;
                            const isChosen = isStudent || isParent;

                            return (
                              <div
                                key={step.id}
                                className={`flex items-center justify-between p-3 rounded-xl border text-sm transition-colors ${
                                  isChosen
                                    ? 'bg-cloud/30 border-ocean/30 text-midnight'
                                    : 'bg-paper/40 border-cloud/40 text-midnight/70'
                                }`}
                              >
                                <div className="flex items-center gap-3">
                                  <span
                                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                                      isChosen
                                        ? 'bg-ocean text-white'
                                        : 'bg-cloud text-midnight/60'
                                    }`}
                                  >
                                    {idx + 1}
                                  </span>
                                  <span className="font-medium text-midnight">
                                    {step.label[storeLang] ?? step.label.en}
                                  </span>
                                </div>

                                {/* Name chips */}
                                <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
                                  {isBoth ? (
                                    <>
                                      <span
                                        className="bg-ocean text-white text-[11px] font-semibold px-2.5 py-0.5 rounded-full truncate max-w-[100px]"
                                        title={studentName}
                                      >
                                        {studentDisplayName}
                                      </span>
                                      <span
                                        className="bg-midnight text-white text-[11px] font-semibold px-2.5 py-0.5 rounded-full truncate max-w-[100px]"
                                        title={parentName}
                                      >
                                        {parentDisplayName}
                                      </span>
                                    </>
                                  ) : isStudent ? (
                                    <span
                                      className="bg-ocean text-white text-[11px] font-semibold px-2.5 py-0.5 rounded-full truncate max-w-[110px]"
                                      title={studentName}
                                    >
                                      {studentDisplayName}
                                    </span>
                                  ) : isParent ? (
                                    <span
                                      className="bg-midnight text-white text-[11px] font-semibold px-2.5 py-0.5 rounded-full truncate max-w-[110px]"
                                      title={parentName}
                                    >
                                      {parentDisplayName}
                                    </span>
                                  ) : null}
                                </div>
                              </div>
                            );
                          })}
                        </div>

                        {/* Summary Sentence */}
                        <p className="text-sm text-midnight/80 font-normal leading-relaxed pt-1">
                          {getScaleSummary(dim)}
                        </p>
                      </div>
                    )}

                    {/* Picks Dimension */}
                    {dim.kind === 'picks' && (
                      <div className="space-y-3.5 pt-1">
                        <div className="flex flex-wrap gap-2">
                          {dim.options.map((opt) => {
                            const isStudent = dim.student_picks.includes(
                              opt.id
                            );
                            const isParent = dim.parent_picks.includes(opt.id);
                            const isBoth = isStudent && isParent;
                            const isPicked = isStudent || isParent;

                            return (
                              <div
                                key={opt.id}
                                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs sm:text-sm font-medium transition-colors ${
                                  isPicked
                                    ? 'bg-cloud/40 border-ocean/40 text-midnight'
                                    : 'bg-paper/30 border-cloud/30 text-midnight/55'
                                }`}
                              >
                                <span>
                                  {opt.label[storeLang] ?? opt.label.en}
                                </span>
                                {isBoth ? (
                                  <div className="flex items-center gap-1 ml-1">
                                    <span
                                      className="bg-ocean text-white text-[10px] font-semibold px-1.5 py-0.5 rounded-md truncate max-w-[80px]"
                                      title={studentName}
                                    >
                                      {studentDisplayName}
                                    </span>
                                    <span
                                      className="bg-midnight text-white text-[10px] font-semibold px-1.5 py-0.5 rounded-md truncate max-w-[80px]"
                                      title={parentName}
                                    >
                                      {parentDisplayName}
                                    </span>
                                  </div>
                                ) : isStudent ? (
                                  <span
                                    className="bg-ocean text-white text-[10px] font-semibold px-1.5 py-0.5 rounded-md ml-1 truncate max-w-[90px]"
                                    title={studentName}
                                  >
                                    {studentDisplayName}
                                  </span>
                                ) : isParent ? (
                                  <span
                                    className="bg-midnight text-white text-[10px] font-semibold px-1.5 py-0.5 rounded-md ml-1 truncate max-w-[90px]"
                                    title={parentName}
                                  >
                                    {parentDisplayName}
                                  </span>
                                ) : null}
                              </div>
                            );
                          })}
                        </div>

                        {/* Shared Domains Sentence */}
                        <p className="text-sm text-midnight/80 font-normal leading-relaxed">
                          {getPicksSharedSentence(dim)}
                        </p>

                        {/* Perception line (omitted if parent_guess is null) */}
                        {dim.parent_guess && (
                          <div className="pt-3 border-t border-cloud/60 space-y-1">
                            <span className="block text-xs font-semibold text-midnight/60">
                              {t.domain_guessLabel
                                .replace('{parent}', parentDisplayName)
                                .replace('{student}', studentDisplayName)}
                            </span>
                            <p className="text-sm text-midnight/80 font-normal leading-relaxed">
                              {getPicksPerceptionSentence(dim)}
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Next step to Explorer */}
        <div className="mt-10 flex justify-center">
          <button
            type="button"
            onClick={() => router.push('/explorer')}
            className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-ocean text-white font-semibold text-base shadow-sm hover:bg-ocean/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ocean transition-all cursor-pointer"
          >
            {t.seeYourOptions} →
          </button>
        </div>

        {/* Footer Note */}
        <footer className="mt-12 pt-6 border-t border-cloud/60 text-center">
          <p className="text-xs text-midnight/60 leading-relaxed max-w-lg mx-auto">
            {t.mirrorFooterNote}
          </p>
        </footer>
      </main>
    </div>
  );
}

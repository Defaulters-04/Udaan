'use client';

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence, MotionConfig } from 'motion/react';
import { useSessionStore } from '@/store/session';
import { getTranslation, type Language } from '@/lib/i18n';
import { Header } from '@/components/Header';
import {
  getQuestions,
  getProgress,
  saveAnswers,
  submitAssessment,
  getStatus,
  ApiError,
  type AssessmentSection,
  type AssessmentQuestion,
  type AnswerValue,
  type LocalizedText,
} from '@/lib/api';

function getLocalizedText(txt: LocalizedText | undefined, lang: Language): string {
  if (!txt) return '';
  return lang === 'hi' && txt.hi ? txt.hi : txt.en;
}

function isQuestionAnswered(q: AssessmentQuestion, val: AnswerValue | undefined): boolean {
  if (val === undefined || val === null) return false;
  if (typeof val === 'string') return val.trim().length > 0;
  if (Array.isArray(val)) return val.length > 0;
  if (typeof val === 'number') return true;
  return false;
}

export default function StudentAssessmentPage() {
  const router = useRouter();

  // Session Store
  const storeRole = useSessionStore((state) => state.role);
  const storeName = useSessionStore((state) => state.name);
  const storeLang = useSessionStore((state) => state.lang);
  const storeFamily = useSessionStore((state) => state.family);
  const hasHydrated = useSessionStore((state) => state.hasHydrated);

  // Assessment flow phases
  const [phase, setPhase] = useState<
    'loading' | 'error' | 'question' | 'interstitial' | 'review' | 'submitting' | 'done'
  >('loading');

  // Question bank and progress state
  const [sections, setSections] = useState<AssessmentSection[]>([]);
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>({});
  const [currentIndex, setCurrentIndex] = useState(0);

  // Interstitial transition state
  const [interstitialInfo, setInterstitialInfo] = useState<{
    prevSectionTitle: string;
    nextSectionTitle: string;
    targetIndex: number;
  } | null>(null);

  // Autosave status state
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'failed'>('idle');

  // UI state for questions
  const [showRequiredError, setShowRequiredError] = useState(false);
  const [selectedSingleChoice, setSelectedSingleChoice] = useState<string | null>(null);
  const [pulseScaleValue, setPulseScaleValue] = useState<number | null>(null);
  const [touchedSliders, setTouchedSliders] = useState<Record<string, boolean>>({});

  // Done phase partner polling state
  const [isPartnerDone, setIsPartnerDone] = useState(false);

  // Refs for timers and debouncing
  const autoAdvanceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const saveDebounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const retryBackoffTimerRef = useRef<NodeJS.Timeout | null>(null);
  const triggerAutosaveRef = useRef<((changedAnswers: Record<string, AnswerValue>) => void) | null>(null);
  const retryCountRef = useRef(0);
  const unsavedAnswersRef = useRef<Record<string, AnswerValue>>({});
  const isTabVisibleRef = useRef(true);
  const answersRef = useRef<Record<string, AnswerValue>>({});

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

  // Flattened questions list
  const flatQuestions = useMemo(() => {
    return sections.flatMap((sec) => sec.questions);
  }, [sections]);

  // Section index by question ID lookup
  const questionToSectionMap = useMemo(() => {
    const map = new Map<string, { section: AssessmentSection; indexInSection: number }>();
    sections.forEach((sec) => {
      sec.questions.forEach((q, idx) => {
        map.set(q.id, { section: sec, indexInSection: idx });
      });
    });
    return map;
  }, [sections]);

  // Guards: redirect if no family or role is parent
  useEffect(() => {
    if (!hasHydrated) return;

    if (!storeFamily) {
      router.replace('/link');
      return;
    }
    if (storeRole === 'parent') {
      router.replace('/intake');
      return;
    }
  }, [hasHydrated, storeFamily, storeRole, router]);

  // Tab visibility listener
  useEffect(() => {
    const handleVis = () => {
      isTabVisibleRef.current = document.visibilityState === 'visible';
    };
    document.addEventListener('visibilitychange', handleVis);
    return () => document.removeEventListener('visibilitychange', handleVis);
  }, []);

  // Autosave execution with retry backoff
  const triggerAutosave = useCallback(
    (changedAnswers: Record<string, AnswerValue>) => {
      if (!storeFamily?.code || !storeFamily?.token) return;

      Object.assign(unsavedAnswersRef.current, changedAnswers);

      if (saveDebounceTimerRef.current) {
        clearTimeout(saveDebounceTimerRef.current);
      }

      setSaveStatus('saving');

      saveDebounceTimerRef.current = setTimeout(async () => {
        const payload = { ...unsavedAnswersRef.current };
        if (Object.keys(payload).length === 0) return;

        try {
          await saveAnswers(storeFamily.code, storeFamily.token, payload);
          // Clear saved keys from unsaved queue
          Object.keys(payload).forEach((k) => delete unsavedAnswersRef.current[k]);
          retryCountRef.current = 0;
          setSaveStatus('saved');
        } catch (err) {
          if (err instanceof ApiError && err.code === 'wrong_role') {
            router.replace('/intake');
            return;
          }
          setSaveStatus('failed');

          // Retry with exponential backoff (1s, 2s, 4s...)
          const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 8000);
          retryCountRef.current += 1;

          if (retryBackoffTimerRef.current) {
            clearTimeout(retryBackoffTimerRef.current);
          }
          retryBackoffTimerRef.current = setTimeout(() => {
            triggerAutosaveRef.current?.({});
          }, delay);
        }
      }, 400);
    },
    [storeFamily, router]
  );

  useEffect(() => {
    triggerAutosaveRef.current = triggerAutosave;
  }, [triggerAutosave]);

  // Update answer in local state and queue autosave
  const setAnswer = useCallback(
    (qId: string, val: AnswerValue) => {
      answersRef.current[qId] = val;
      setAnswers((prev) => {
        const next = { ...prev, [qId]: val };
        return next;
      });
      setShowRequiredError(false);
      triggerAutosave({ [qId]: val });
    },
    [triggerAutosave]
  );

  // Load questions and resume progress asynchronously
  const loadData = useCallback(() => {
    if (!storeFamily?.code || !storeFamily?.token) return;

    Promise.all([
      getQuestions(storeFamily.code, storeFamily.token),
      getProgress(storeFamily.code, storeFamily.token),
    ])
      .then(([qRes, pRes]) => {
        setSections(qRes.sections);
        setAnswers(pRes.answers || {});
        answersRef.current = { ...(pRes.answers || {}) };

        if (pRes.submitted) {
          setPhase('done');
          return;
        }

        const all = qRes.sections.flatMap((s) => s.questions);
        // Resume at the first unanswered question
        const firstUnansweredIndex = all.findIndex(
          (q) => !isQuestionAnswered(q, pRes.answers?.[q.id])
        );

        if (firstUnansweredIndex !== -1) {
          setCurrentIndex(firstUnansweredIndex);
          setPhase('question');
        } else {
          // All answered, show review
          setCurrentIndex(all.length - 1);
          setPhase('review');
        }
      })
      .catch((err) => {
        if (err instanceof ApiError && err.code === 'wrong_role') {
          router.replace('/intake');
          return;
        }
        setPhase('error');
      });
  }, [storeFamily, router]);

  useEffect(() => {
    if (hasHydrated && storeFamily && storeRole === 'student') {
      loadData();
    }
  }, [hasHydrated, storeFamily, storeRole, loadData]);

  // Cancel pending auto-advance timer
  const cancelAutoAdvance = useCallback(() => {
    if (autoAdvanceTimerRef.current) {
      clearTimeout(autoAdvanceTimerRef.current);
      autoAdvanceTimerRef.current = null;
    }
  }, []);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      cancelAutoAdvance();
      if (saveDebounceTimerRef.current) clearTimeout(saveDebounceTimerRef.current);
      if (retryBackoffTimerRef.current) clearTimeout(retryBackoffTimerRef.current);
    };
  }, [cancelAutoAdvance]);

  // Navigate to target question, checking for section interstitial
  const navigateToQuestion = useCallback(
    (targetIndex: number) => {
      cancelAutoAdvance();
      setShowRequiredError(false);
      setSelectedSingleChoice(null);
      setPulseScaleValue(null);

      if (targetIndex >= flatQuestions.length) {
        setPhase('review');
        return;
      }

      if (targetIndex < 0) return;

      const currentQ = flatQuestions[currentIndex];
      const targetQ = flatQuestions[targetIndex];

      // Check if advancing across a section boundary
      if (targetIndex > currentIndex && currentQ && targetQ && currentQ.section_id !== targetQ.section_id) {
        const prevSec = questionToSectionMap.get(currentQ.id)?.section;
        const nextSec = questionToSectionMap.get(targetQ.id)?.section;

        if (prevSec && nextSec) {
          setInterstitialInfo({
            prevSectionTitle: getLocalizedText(prevSec.title, storeLang),
            nextSectionTitle: getLocalizedText(nextSec.title, storeLang),
            targetIndex,
          });
          setPhase('interstitial');
          return;
        }
      }

      setCurrentIndex(targetIndex);
      setPhase('question');
    },
    [cancelAutoAdvance, flatQuestions, currentIndex, questionToSectionMap, storeLang]
  );

  // Handle interstitial auto-advance
  useEffect(() => {
    if (phase !== 'interstitial' || !interstitialInfo) return;

    const timer = setTimeout(() => {
      setCurrentIndex(interstitialInfo.targetIndex);
      setPhase('question');
      setInterstitialInfo(null);
    }, 1400);

    return () => clearTimeout(timer);
  }, [phase, interstitialInfo]);

  const skipInterstitial = useCallback(() => {
    if (interstitialInfo) {
      setCurrentIndex(interstitialInfo.targetIndex);
      setPhase('question');
      setInterstitialInfo(null);
    }
  }, [interstitialInfo]);

  // Handle "Continue" click on current question
  const handleContinue = useCallback(() => {
    const q = flatQuestions[currentIndex];
    if (!q) return;

    const val = answersRef.current[q.id] !== undefined ? answersRef.current[q.id] : answers[q.id];
    const answered = isQuestionAnswered(q, val);

    if (q.required && !answered) {
      setShowRequiredError(true);
      return;
    }

    setShowRequiredError(false);
    navigateToQuestion(currentIndex + 1);
  }, [flatQuestions, currentIndex, answers, navigateToQuestion]);

  // Handle "Back" click
  const handleBack = useCallback(() => {
    cancelAutoAdvance();
    if (currentIndex > 0) {
      navigateToQuestion(currentIndex - 1);
    }
  }, [cancelAutoAdvance, currentIndex, navigateToQuestion]);

  // Handle "Skip" on optional question
  const handleSkip = useCallback(() => {
    cancelAutoAdvance();
    navigateToQuestion(currentIndex + 1);
  }, [cancelAutoAdvance, currentIndex, navigateToQuestion]);

  // Auto-advance helper for single_choice and scale
  const scheduleAutoAdvance = useCallback(
    (targetIndex: number, delayMs = 450) => {
      cancelAutoAdvance();
      setShowRequiredError(false);
      autoAdvanceTimerRef.current = setTimeout(() => {
        navigateToQuestion(targetIndex);
      }, delayMs);
    },
    [cancelAutoAdvance, navigateToQuestion]
  );

  // Handle Single Choice selection
  const handleSelectSingleChoice = useCallback(
    (optId: string) => {
      const q = flatQuestions[currentIndex];
      if (!q) return;

      setSelectedSingleChoice(optId);
      setAnswer(q.id, optId);
      scheduleAutoAdvance(currentIndex + 1, 450);
    },
    [flatQuestions, currentIndex, setAnswer, scheduleAutoAdvance]
  );

  // Handle Scale selection
  const handleSelectScale = useCallback(
    (num: number) => {
      const q = flatQuestions[currentIndex];
      if (!q) return;

      setPulseScaleValue(num);
      setAnswer(q.id, num);
      scheduleAutoAdvance(currentIndex + 1, 450);
    },
    [flatQuestions, currentIndex, setAnswer, scheduleAutoAdvance]
  );

  // Handle Multi Choice toggle
  const handleToggleMultiChoice = useCallback(
    (optId: string) => {
      const q = flatQuestions[currentIndex];
      if (!q) return;

      const curr = ((answersRef.current[q.id] !== undefined ? answersRef.current[q.id] : answers[q.id]) as string[]) || [];
      const next = curr.includes(optId)
        ? curr.filter((id) => id !== optId)
        : [...curr, optId];

      setAnswer(q.id, next);
    },
    [flatQuestions, currentIndex, answers, setAnswer]
  );

  // Keyboard navigation listener (1-9 number keys, Enter, Backspace/Escape)
  useEffect(() => {
    if (phase === 'interstitial') {
      const handleKey = (e: KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') {
          skipInterstitial();
        }
      };
      window.addEventListener('keydown', handleKey);
      return () => window.removeEventListener('keydown', handleKey);
    }

    if (phase !== 'question') return;

    const currentQ = flatQuestions[currentIndex];
    if (!currentQ) return;

    const handleKey = (e: KeyboardEvent) => {
      // Don't intercept if user is typing in input or textarea
      const targetTag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (targetTag === 'input' || targetTag === 'textarea') {
        if (e.key === 'Enter' && targetTag === 'input') {
          e.preventDefault();
          handleContinue();
        }
        return;
      }

      if (e.key === 'Enter') {
        e.preventDefault();
        handleContinue();
        return;
      }

      if (currentQ.type === 'single_choice' && currentQ.options) {
        const num = parseInt(e.key, 10);
        if (!isNaN(num) && num >= 1 && num <= currentQ.options.length) {
          e.preventDefault();
          handleSelectSingleChoice(currentQ.options[num - 1].id);
        }
      }

      if (currentQ.type === 'scale') {
        const minVal = currentQ.min ?? 1;
        const maxVal = currentQ.max ?? 5;
        const num = parseInt(e.key, 10);
        if (!isNaN(num) && num >= minVal && num <= maxVal) {
          e.preventDefault();
          handleSelectScale(num);
        }
      }
    };

    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [
    phase,
    flatQuestions,
    currentIndex,
    handleContinue,
    handleSelectSingleChoice,
    handleSelectScale,
    skipInterstitial,
  ]);

  // Submit assessment handler
  const handleSubmit = async () => {
    if (!storeFamily?.code || !storeFamily?.token) return;

    setPhase('submitting');
    try {
      await submitAssessment(storeFamily.code, storeFamily.token);
      setPhase('done');
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === 'wrong_role') {
          router.replace('/intake');
          return;
        }
        if (err.code === 'assessment_incomplete' && err.missing && err.missing.length > 0) {
          // Jump to first missing question
          const missingId = err.missing[0];
          const missingIdx = flatQuestions.findIndex((q) => q.id === missingId);
          if (missingIdx !== -1) {
            setCurrentIndex(missingIdx);
            setShowRequiredError(true);
            setPhase('question');
            return;
          }
        }
      }
      setPhase('review');
    }
  };

  // Poll status in done state every 2s
  useEffect(() => {
    if (phase !== 'done' || !storeFamily?.code || !storeFamily?.token) return;

    const timer = setInterval(async () => {
      if (!isTabVisibleRef.current) return;
      try {
        const status = await getStatus(storeFamily.code, storeFamily.token);
        if (status.partner?.done) {
          setIsPartnerDone(true);
        }
      } catch {
        // Ignore poll failures
      }
    }, 2000);

    return () => clearInterval(timer);
  }, [phase, storeFamily]);

  // Current question data
  const currentQ = flatQuestions[currentIndex];
  const sectionInfo = currentQ ? questionToSectionMap.get(currentQ.id) : null;
  const currentAnswer = currentQ ? answers[currentQ.id] : undefined;

  // Calculate section progress counts for rail and review
  const sectionStats = useMemo(() => {
    return sections.map((sec) => {
      const total = sec.questions.length;
      const answered = sec.questions.filter((q) => isQuestionAnswered(q, answers[q.id])).length;
      const startIndex = flatQuestions.findIndex((q) => q.section_id === sec.id);
      return {
        section: sec,
        total,
        answered,
        startIndex,
      };
    });
  }, [sections, answers, flatQuestions]);

  if (!hasHydrated || phase === 'loading') {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-cloud border-t-ocean animate-spin" />
      </div>
    );
  }

  if (phase === 'error') {
    return (
      <div className="min-h-screen bg-paper text-midnight flex flex-col justify-between">
        <main className="w-full max-w-[600px] mx-auto px-5 sm:px-6 pt-10 sm:pt-16 pb-12 flex-1 flex flex-col">
          <Header />
          <div className="p-6 bg-white border-2 border-cloud rounded-2xl space-y-4 my-auto text-center">
            <p className="text-base font-medium text-midnight">{t.loadFailed}</p>
            <button
              type="button"
              onClick={() => {
                setPhase('loading');
                loadData();
              }}
              className="px-6 py-2.5 bg-ocean text-white font-medium rounded-xl hover:bg-ocean/90 focus-visible:outline-2 focus-visible:outline-ocean cursor-pointer"
            >
              {t.retry}
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <MotionConfig reducedMotion="user">
      <div className="min-h-screen bg-paper text-midnight selection:bg-sky/20 flex flex-col justify-between">
        <main className="w-full max-w-[600px] mx-auto px-5 sm:px-6 pt-6 sm:pt-10 pb-12 flex-1 flex flex-col">
          {/* Header */}
          <Header />

          {/* ======================================================== */}
          {/* PHASE: INTERSTITIAL (Calm Section Completion)             */}
          {/* ======================================================== */}
          {phase === 'interstitial' && interstitialInfo && (
            <div
              onClick={skipInterstitial}
              className="flex-1 flex flex-col items-center justify-center text-center py-16 cursor-pointer select-none"
            >
              <div className="space-y-4 w-full max-w-sm">
                <h2 className={`${headingFontClass} text-2xl sm:text-3xl font-bold text-midnight`}>
                  {interstitialInfo.prevSectionTitle}
                </h2>
                <p className="text-base text-midnight/70 font-normal">
                  {interstitialInfo.nextSectionTitle}
                </p>

                {/* Smooth 1.4s animated ocean line */}
                <div className="w-full h-1 bg-cloud rounded-full overflow-hidden mt-6">
                  <motion.div
                    className="h-full bg-ocean"
                    initial={{ width: '0%' }}
                    animate={{ width: '100%' }}
                    transition={{ duration: 1.4, ease: 'linear' }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* PHASE: QUESTION FLOW                                     */}
          {/* ======================================================== */}
          {phase === 'question' && currentQ && (
            <div className="flex-1 flex flex-col">
              {/* Progress Rail Header */}
              <div className="mb-8 space-y-2.5">
                <div className="flex items-center justify-between text-xs text-midnight/70 font-medium">
                  <span>{sectionInfo ? getLocalizedText(sectionInfo.section.title, storeLang) : ''}</span>
                  <div className="flex items-center gap-3">
                    {/* Autosave status indicator */}
                    <span className="text-[11px] text-midnight/55 transition-opacity">
                      {saveStatus === 'saving' && t.saving}
                      {saveStatus === 'saved' && t.saved}
                      {saveStatus === 'failed' && t.saveFailed}
                    </span>
                    <span>
                      {t.questionOf
                        .replace('{n}', (currentIndex + 1).toString())
                        .replace('{total}', flatQuestions.length.toString())}
                    </span>
                  </div>
                </div>

                {/* 5-segment rail proportional to question counts */}
                <div className="flex gap-1.5 h-1.5 w-full">
                  {sectionStats.map((stat, idx) => {
                    const isPassed = currentIndex > stat.startIndex + stat.total - 1;
                    const isCurrent =
                      currentIndex >= stat.startIndex && currentIndex < stat.startIndex + stat.total;
                    const fillPercent = isPassed
                      ? 100
                      : isCurrent
                      ? ((currentIndex - stat.startIndex + 1) / stat.total) * 100
                      : 0;

                    return (
                      <div
                        key={idx}
                        className="h-full bg-cloud rounded-full overflow-hidden"
                        style={{ flex: stat.total }}
                      >
                        <motion.div
                          className="h-full bg-ocean"
                          initial={false}
                          animate={{ width: `${fillPercent}%` }}
                          transition={{ duration: 0.3, ease: 'easeOut' }}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Animated Question Body */}
              <div className="flex-1 flex flex-col">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={currentQ.id}
                    initial={{ x: 24, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: -24, opacity: 0 }}
                    transition={{ duration: 0.3, ease: 'easeOut' }}
                    className="flex-1 flex flex-col justify-between space-y-8"
                  >
                    {/* Question Prompt */}
                    <div className="space-y-3">
                      <motion.h2
                        initial={{ y: 12, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        transition={{ duration: 0.3, ease: 'easeOut' }}
                        className={`${headingFontClass} text-xl sm:text-2xl font-semibold text-midnight leading-snug`}
                      >
                        {getLocalizedText(currentQ.prompt, storeLang)}
                      </motion.h2>

                      {/* Gentle Required Warning */}
                      {showRequiredError && (
                        <p role="alert" className="text-xs sm:text-sm text-red-600 font-medium">
                          {t.required}
                        </p>
                      )}
                    </div>

                    {/* Question Controls by Type */}
                    <div className="flex-1">
                      {/* TYPE 1: SINGLE CHOICE */}
                      {currentQ.type === 'single_choice' && currentQ.options && (
                        <div className="space-y-3">
                          {currentQ.options.map((opt, optIdx) => {
                            const isSelected =
                              selectedSingleChoice === opt.id || currentAnswer === opt.id;
                            const isDimmed =
                              selectedSingleChoice !== null && selectedSingleChoice !== opt.id;

                            return (
                              <motion.button
                                key={opt.id}
                                initial={{ y: 12, opacity: 0 }}
                                animate={{
                                  y: 0,
                                  opacity: isDimmed ? 0.6 : 1,
                                }}
                                transition={{
                                  duration: 0.25,
                                  delay: optIdx * 0.04,
                                  ease: 'easeOut',
                                }}
                                type="button"
                                onClick={() => handleSelectSingleChoice(opt.id)}
                                className={`w-full min-h-[56px] p-3.5 sm:p-4 rounded-xl border-2 flex items-center justify-between transition-colors text-left cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ocean ${
                                  isSelected
                                    ? 'bg-sky-tint border-ocean text-midnight'
                                    : 'bg-white border-cloud hover:border-sky/70 text-midnight'
                                }`}
                              >
                                <div className="flex items-center gap-3">
                                  <span className="w-7 h-7 rounded-md bg-cloud/70 font-mono text-xs font-semibold text-midnight flex items-center justify-center shrink-0">
                                    {optIdx + 1}
                                  </span>
                                  <span className="text-sm sm:text-base font-normal">
                                    {getLocalizedText(opt.label, storeLang)}
                                  </span>
                                </div>

                                {/* Animated Checkmark SVG */}
                                {isSelected && (
                                  <svg
                                    className="w-5 h-5 text-ocean shrink-0 ml-2"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="3"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                  >
                                    <motion.path
                                      d="M20 6L9 17l-5-5"
                                      initial={{ pathLength: 0 }}
                                      animate={{ pathLength: 1 }}
                                      transition={{ duration: 0.25, ease: 'easeOut' }}
                                    />
                                  </svg>
                                )}
                              </motion.button>
                            );
                          })}
                        </div>
                      )}

                      {/* TYPE 2: SCALE (Row of circles 1 to max) */}
                      {currentQ.type === 'scale' && (
                        <div className="py-6 space-y-6">
                          <div className="flex items-center justify-between gap-2 max-w-md mx-auto">
                            {Array.from(
                              { length: (currentQ.max ?? 5) - (currentQ.min ?? 1) + 1 },
                              (_, i) => (currentQ.min ?? 1) + i
                            ).map((num) => {
                              const isSelected =
                                pulseScaleValue === num || currentAnswer === num;

                              return (
                                <motion.button
                                  key={num}
                                  type="button"
                                  onClick={() => handleSelectScale(num)}
                                  animate={
                                    isSelected
                                      ? {
                                          scale: [1, 1.15, 1.08],
                                          boxShadow: '0 0 0 4px rgba(125, 190, 240, 0.45)',
                                        }
                                      : { scale: 1, boxShadow: 'none' }
                                  }
                                  transition={{ duration: 0.3 }}
                                  className={`w-12 h-12 sm:w-14 sm:h-14 rounded-full border-2 font-mono font-semibold text-base sm:text-lg flex items-center justify-center transition-colors cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ocean ${
                                    isSelected
                                      ? 'bg-sky-tint border-ocean text-midnight'
                                      : 'bg-white border-cloud hover:border-sky text-midnight'
                                  }`}
                                >
                                  {num}
                                </motion.button>
                              );
                            })}
                          </div>

                          <div className="flex justify-between text-xs sm:text-sm text-midnight/70 font-normal px-2">
                            <span>{getLocalizedText(currentQ.min_label, storeLang)}</span>
                            <span>{getLocalizedText(currentQ.max_label, storeLang)}</span>
                          </div>
                        </div>
                      )}

                      {/* TYPE 3: SLIDER */}
                      {currentQ.type === 'slider' && (
                        <div className="py-8 space-y-6 max-w-lg mx-auto">
                          <div className="relative pt-6">
                            {/* Floating Value Bubble */}
                            <div
                              className="absolute -top-3 -translate-x-1/2 bg-ocean text-white font-mono text-xs px-2.5 py-1 rounded-md shadow-sm pointer-events-none"
                              style={{
                                left: `${
                                  (((typeof currentAnswer === 'number'
                                    ? currentAnswer
                                    : (currentQ.min ?? 0)) -
                                    (currentQ.min ?? 0)) /
                                    ((currentQ.max ?? 100) - (currentQ.min ?? 0))) *
                                  100
                                }%`,
                              }}
                            >
                              {typeof currentAnswer === 'number'
                                ? currentAnswer
                                : currentQ.min ?? 0}
                            </div>

                            {/* Native Range Slider with Ocean styling */}
                            <input
                              type="range"
                              min={currentQ.min ?? 0}
                              max={currentQ.max ?? 100}
                              step={currentQ.step ?? 1}
                              value={
                                typeof currentAnswer === 'number'
                                  ? currentAnswer
                                  : currentQ.min ?? 0
                              }
                              onChange={(e) => {
                                const val = Number(e.target.value);
                                setTouchedSliders((prev) => ({ ...prev, [currentQ.id]: true }));
                                setAnswer(currentQ.id, val);
                              }}
                              className="w-full h-2 bg-cloud rounded-lg appearance-none cursor-pointer accent-ocean focus-visible:outline-2 focus-visible:outline-ocean"
                            />
                          </div>

                          <div className="flex justify-between text-xs sm:text-sm text-midnight/70">
                            <span>{getLocalizedText(currentQ.min_label, storeLang)}</span>
                            <span>{getLocalizedText(currentQ.max_label, storeLang)}</span>
                          </div>
                        </div>
                      )}

                      {/* TYPE 4: MULTI CHOICE */}
                      {currentQ.type === 'multi_choice' && currentQ.options && (
                        <div className="space-y-3">
                          {currentQ.options.map((opt, optIdx) => {
                            const selectedList = (currentAnswer as string[]) || [];
                            const isSelected = selectedList.includes(opt.id);

                            return (
                              <motion.button
                                key={opt.id}
                                initial={{ y: 12, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                                transition={{
                                  duration: 0.25,
                                  delay: optIdx * 0.04,
                                  ease: 'easeOut',
                                }}
                                type="button"
                                onClick={() => handleToggleMultiChoice(opt.id)}
                                className={`w-full min-h-[52px] p-3.5 sm:p-4 rounded-xl border-2 flex items-center justify-between transition-colors text-left cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ocean ${
                                  isSelected
                                    ? 'bg-sky-tint border-ocean text-midnight'
                                    : 'bg-white border-cloud hover:border-sky/70 text-midnight'
                                }`}
                              >
                                <span className="text-sm sm:text-base font-normal">
                                  {getLocalizedText(opt.label, storeLang)}
                                </span>
                                <div
                                  className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                                    isSelected
                                      ? 'border-ocean bg-ocean text-white'
                                      : 'border-cloud bg-white'
                                  }`}
                                >
                                  {isSelected && (
                                    <svg
                                      className="w-3.5 h-3.5"
                                      fill="none"
                                      viewBox="0 0 24 24"
                                      stroke="currentColor"
                                      strokeWidth="3.5"
                                    >
                                      <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        d="M5 13l4 4L19 7"
                                      />
                                    </svg>
                                  )}
                                </div>
                              </motion.button>
                            );
                          })}
                        </div>
                      )}

                      {/* TYPE 5: SHORT TEXT */}
                      {currentQ.type === 'text' && (
                        <div className="space-y-3">
                          <input
                            type="text"
                            value={(currentAnswer as string) || ''}
                            onChange={(e) => setAnswer(currentQ.id, e.target.value)}
                            placeholder={getLocalizedText(currentQ.placeholder, storeLang)}
                            className="w-full px-4 py-3 bg-white border-2 border-cloud rounded-xl text-base text-midnight placeholder:text-midnight/40 focus:border-ocean focus-visible:outline-2 focus-visible:outline-ocean transition-colors"
                          />
                        </div>
                      )}

                      {/* TYPE 6: LONG TEXT */}
                      {currentQ.type === 'long_text' && (
                        <div className="space-y-2">
                          <textarea
                            rows={4}
                            maxLength={currentQ.max_length ?? 300}
                            value={(currentAnswer as string) || ''}
                            onChange={(e) => setAnswer(currentQ.id, e.target.value)}
                            placeholder={getLocalizedText(currentQ.placeholder, storeLang)}
                            className="w-full p-4 bg-white border-2 border-cloud rounded-xl text-base text-midnight placeholder:text-midnight/40 focus:border-ocean focus-visible:outline-2 focus-visible:outline-ocean transition-colors resize-none"
                          />
                          <div className="flex justify-end text-xs text-midnight/50 font-mono">
                            {((currentAnswer as string) || '').length} / {currentQ.max_length ?? 300}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Bottom Action Controls */}
                    <div className="pt-6 flex items-center justify-between gap-4 border-t border-cloud/60">
                      <div>
                        {currentIndex > 0 ? (
                          <button
                            type="button"
                            onClick={handleBack}
                            className="px-4 py-2 text-sm font-medium text-midnight/70 hover:text-midnight rounded-lg transition-colors focus-visible:outline-2 focus-visible:outline-ocean cursor-pointer"
                          >
                            ← {t.back}
                          </button>
                        ) : (
                          <div />
                        )}
                      </div>

                      <div className="flex items-center gap-3">
                        {!currentQ.required && (
                          <button
                            type="button"
                            onClick={handleSkip}
                            className="px-4 py-2 text-sm font-medium text-midnight/60 hover:text-midnight rounded-lg transition-colors focus-visible:outline-2 focus-visible:outline-ocean cursor-pointer"
                          >
                            {t.skip}
                          </button>
                        )}

                        {/* Continue Button for types that don't auto-advance or optional manual continue */}
                        {(currentQ.type === 'multi_choice' ||
                          currentQ.type === 'slider' ||
                          currentQ.type === 'text' ||
                          currentQ.type === 'long_text') && (
                          <button
                            type="button"
                            onClick={handleContinue}
                            disabled={
                              currentQ.type === 'slider' &&
                              currentQ.required &&
                              !touchedSliders[currentQ.id] &&
                              currentAnswer === undefined
                            }
                            className={`px-6 py-2.5 rounded-xl text-sm sm:text-base font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-ocean ${
                              currentQ.type === 'slider' &&
                              currentQ.required &&
                              !touchedSliders[currentQ.id] &&
                              currentAnswer === undefined
                                ? 'bg-cloud text-midnight/40 cursor-not-allowed'
                                : 'bg-ocean text-white hover:bg-[#255ba0] cursor-pointer'
                            }`}
                          >
                            {t.continue}
                          </button>
                        )}
                      </div>
                    </div>
                  </motion.div>
                </AnimatePresence>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* PHASE: REVIEW SCREEN                                     */}
          {/* ======================================================== */}
          {(phase === 'review' || phase === 'submitting') && (
            <div className="flex-1 flex flex-col justify-between space-y-8">
              <div className="space-y-6">
                <div className="space-y-2">
                  <h2 className={`${headingFontClass} text-2xl sm:text-3xl font-bold text-midnight tracking-tight`}>
                    {t.reviewTitle}
                  </h2>
                  <p className="text-sm sm:text-base text-midnight/70">
                    {t.reviewBody}
                  </p>
                </div>

                {/* 5 Section Summary Rows */}
                <div className="space-y-3">
                  {sectionStats.map((stat) => {
                    const isAllDone = stat.answered === stat.total;

                    return (
                      <button
                        key={stat.section.id}
                        type="button"
                        onClick={() => {
                          if (stat.startIndex !== -1) {
                            setCurrentIndex(stat.startIndex);
                            setPhase('question');
                          }
                        }}
                        className="w-full p-4 sm:p-5 bg-white border-2 border-cloud hover:border-ocean/60 rounded-xl flex items-center justify-between text-left transition-colors focus-visible:outline-2 focus-visible:outline-ocean cursor-pointer"
                      >
                        <div className="space-y-0.5">
                          <h3 className="text-base font-semibold text-midnight">
                            {getLocalizedText(stat.section.title, storeLang)}
                          </h3>
                          <p className="text-xs sm:text-sm text-midnight/60 font-normal">
                            {t.answeredOf
                              .replace('{answered}', stat.answered.toString())
                              .replace('{total}', stat.total.toString())}
                          </p>
                        </div>

                        <div className="flex items-center gap-2">
                          {isAllDone && (
                            <span className="text-xs bg-sky-tint text-ocean px-2 py-0.5 rounded font-medium">
                              ✓
                            </span>
                          )}
                          <span className="text-sm font-semibold text-ocean">
                            {t.edit} →
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Submit Button */}
              <div className="pt-4 border-t border-cloud/70">
                <button
                  type="button"
                  disabled={phase === 'submitting'}
                  onClick={handleSubmit}
                  className="w-full py-3.5 px-6 bg-ocean text-white font-semibold text-base rounded-xl hover:bg-[#255ba0] transition-colors focus-visible:outline-2 focus-visible:outline-ocean cursor-pointer"
                >
                  {phase === 'submitting' ? t.submitting : t.submit}
                </button>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* PHASE: DONE SCREEN                                       */}
          {/* ======================================================== */}
          {phase === 'done' && (
            <div className="flex-1 flex flex-col justify-center items-center text-center space-y-6 py-12">
              <div className="w-16 h-16 rounded-full bg-sky-tint border-2 border-ocean flex items-center justify-center text-ocean text-2xl font-bold">
                ✓
              </div>

              <div className="space-y-2 max-w-md">
                <h2 className={`${headingFontClass} text-2xl sm:text-3xl font-bold text-midnight tracking-tight`}>
                  {t.doneTitle.replace('{name}', storeName || 'Student')}
                </h2>

                <p className="text-base text-midnight/70">
                  {isPartnerDone ? t.bothDone : t.waitingParentDone}
                </p>
              </div>

              {isPartnerDone ? (
                <div className="pt-4">
                  <button
                    type="button"
                    onClick={() => router.push('/mirror')}
                    className="px-8 py-3.5 bg-ocean text-white font-semibold text-base rounded-xl hover:bg-[#255ba0] transition-colors focus-visible:outline-2 focus-visible:outline-ocean cursor-pointer"
                  >
                    {t.compare} →
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2.5 p-3.5 bg-cloud/60 rounded-xl text-sm text-midnight/80">
                  <span className="w-2.5 h-2.5 rounded-full bg-ocean animate-pulse" />
                  <span>{t.waitingParentDone}</span>
                </div>
              )}
            </div>
          )}

          {/* Consent Footnote */}
          <footer className="mt-12 sm:mt-16 pt-6 border-t border-cloud/70 text-xs sm:text-sm text-midnight/65 leading-relaxed">
            <p>{t.consent}</p>
          </footer>
        </main>
      </div>
    </MotionConfig>
  );
}

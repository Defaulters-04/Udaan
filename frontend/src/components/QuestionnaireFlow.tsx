'use client';

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence, MotionConfig } from 'motion/react';
import { useSessionStore, type Role } from '@/store/session';
import { getTranslation, type Language } from '@/lib/i18n';
import { Header } from '@/components/Header';
import {
  getStatus,
  ApiError,
  type AssessmentSection,
  type AssessmentQuestion,
  type AssessmentQuestionsResponse,
  type AssessmentProgressResponse,
  type SaveAnswersResponse,
  type SubmitAssessmentResponse,
  type AnswerValue,
  type LocalizedText,
} from '@/lib/api';

export function getLocalizedText(txt: LocalizedText | undefined, lang: Language): string {
  if (!txt) return '';
  return lang === 'hi' && txt.hi ? txt.hi : txt.en;
}

export function isQuestionAnswered(q: AssessmentQuestion, val: AnswerValue | undefined): boolean {
  if (val === undefined || val === null) return false;
  if (typeof val === 'string') return val.trim().length > 0;
  if (Array.isArray(val)) return val.length > 0;
  if (typeof val === 'number') return true;
  return false;
}

export function formatAnswerText(
  q: AssessmentQuestion,
  val: AnswerValue | undefined,
  lang: Language,
  skippedText: string
): string {
  if (
    val === undefined ||
    val === null ||
    val === '' ||
    (Array.isArray(val) && val.length === 0)
  ) {
    return skippedText;
  }
  if (q.type === 'single_choice' && q.options) {
    const opt = q.options.find((o) => o.id === val);
    return opt ? getLocalizedText(opt.label, lang) : String(val);
  }
  if (q.type === 'multi_choice' && q.options && Array.isArray(val)) {
    const labels = val
      .map((id) => {
        const opt = q.options?.find((o) => o.id === id);
        return opt ? getLocalizedText(opt.label, lang) : id;
      })
      .filter(Boolean);
    return labels.length > 0 ? labels.join(', ') : skippedText;
  }
  if (typeof val === 'number') {
    return String(val);
  }
  if (typeof val === 'string') {
    return val.trim() || skippedText;
  }
  return String(val);
}

export interface QuestionnaireConfig {
  role: Role;
  wrongRoleRedirect: string;
  getQuestions: (code: string, token: string) => Promise<AssessmentQuestionsResponse>;
  getProgress: (code: string, token: string) => Promise<AssessmentProgressResponse>;
  saveAnswers: (
    code: string,
    token: string,
    answers: Record<string, AnswerValue>
  ) => Promise<SaveAnswersResponse>;
  submit: (code: string, token: string) => Promise<SubmitAssessmentResponse>;
  incompleteErrorCode: 'assessment_incomplete' | 'intake_incomplete';
  reviewType: 'student' | 'parent';
  partnerWaitingTextKey: 'waitingParentDone' | 'waitingStudentDone';
  showPrivacyIntakeOnFirstQuestion?: boolean;
}

interface QuestionnaireFlowProps {
  config: QuestionnaireConfig;
}

export function QuestionnaireFlow({ config }: QuestionnaireFlowProps) {
  const router = useRouter();

  // Session Store
  const storeRole = useSessionStore((state) => state.role);
  const storeName = useSessionStore((state) => state.name);
  const storeLang = useSessionStore((state) => state.lang);
  const storeFamily = useSessionStore((state) => state.family);
  const hasHydrated = useSessionStore((state) => state.hasHydrated);

  // Flow phases
  const [phase, setPhase] = useState<
    'loading' | 'error' | 'question' | 'interstitial' | 'review' | 'submitting' | 'done'
  >('loading');

  // Question bank and progress state
  const [sections, setSections] = useState<AssessmentSection[]>([]);
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>({});
  const [currentIndex, setCurrentIndex] = useState(0);

  // Return to review flag when editing a question from confirmation screen
  const [isEditingFromReview, setIsEditingFromReview] = useState(false);

  // Interstitial transition state
  const [interstitialInfo, setInterstitialInfo] = useState<{
    prevSectionTitle: LocalizedText;
    nextSectionTitle: LocalizedText;
    targetIndex: number;
  } | null>(null);

  // Autosave status state
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'failed'>('idle');

  // UI state for questions
  const [showRequiredError, setShowRequiredError] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [selectedSingleChoice, setSelectedSingleChoice] = useState<string | null>(null);
  const [pulseScaleValue, setPulseScaleValue] = useState<number | null>(null);
  const [touchedSliders, setTouchedSliders] = useState<Record<string, boolean>>({});

  // Done phase partner polling state
  const [isPartnerDone, setIsPartnerDone] = useState(false);

  // Timers and refs
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

  // Guards: redirect if no family or role is wrong
  useEffect(() => {
    if (!hasHydrated) return;

    if (!storeFamily) {
      router.replace('/link');
      return;
    }
    if (storeRole !== config.role) {
      router.replace(config.wrongRoleRedirect);
      return;
    }
  }, [hasHydrated, storeFamily, storeRole, router, config.role, config.wrongRoleRedirect]);

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
          await config.saveAnswers(storeFamily.code, storeFamily.token, payload);
          Object.keys(payload).forEach((k) => delete unsavedAnswersRef.current[k]);
          retryCountRef.current = 0;
          setSaveStatus('saved');
        } catch (err) {
          if (err instanceof ApiError && err.code === 'wrong_role') {
            router.replace(config.wrongRoleRedirect);
            return;
          }
          setSaveStatus('failed');

          // Exponential backoff
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
    [storeFamily, router, config]
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
      config.getQuestions(storeFamily.code, storeFamily.token),
      config.getProgress(storeFamily.code, storeFamily.token),
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
          router.replace(config.wrongRoleRedirect);
          return;
        }
        setPhase('error');
      });
  }, [storeFamily, router, config]);

  useEffect(() => {
    if (hasHydrated && storeFamily && storeRole === config.role) {
      loadData();
    }
  }, [hasHydrated, storeFamily, storeRole, loadData, config.role]);

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

      const prevSec = currentQ ? questionToSectionMap.get(currentQ.id)?.section : undefined;
      const nextSec = targetQ ? questionToSectionMap.get(targetQ.id)?.section : undefined;

      // Check if advancing across a section boundary
      if (
        targetIndex > currentIndex &&
        prevSec &&
        nextSec &&
        prevSec.id !== nextSec.id
      ) {
        setInterstitialInfo({
          prevSectionTitle: prevSec.title,
          nextSectionTitle: nextSec.title,
          targetIndex,
        });
        setPhase('interstitial');
        return;
      }

      setCurrentIndex(targetIndex);
      setPhase('question');
    },
    [cancelAutoAdvance, flatQuestions, currentIndex, questionToSectionMap]
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

  // Return back to review screen from edit mode
  const handleReturnToReview = useCallback(() => {
    cancelAutoAdvance();
    setIsEditingFromReview(false);
    setShowRequiredError(false);
    setSelectedSingleChoice(null);
    setPulseScaleValue(null);
    setPhase('review');
  }, [cancelAutoAdvance]);

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

    // If at the end of questions, return to review
    if (currentIndex >= flatQuestions.length - 1) {
      setIsEditingFromReview(false);
      setPhase('review');
      return;
    }

    navigateToQuestion(currentIndex + 1);
  }, [flatQuestions, currentIndex, answers, navigateToQuestion]);

  // Handle "Back" click
  const handleBack = useCallback(() => {
    cancelAutoAdvance();
    if (currentIndex > 0) {
      navigateToQuestion(currentIndex - 1);
    } else if (isEditingFromReview) {
      handleReturnToReview();
    }
  }, [cancelAutoAdvance, currentIndex, isEditingFromReview, navigateToQuestion, handleReturnToReview]);

  // Handle "Skip" on optional question
  const handleSkip = useCallback(() => {
    cancelAutoAdvance();
    if (currentIndex >= flatQuestions.length - 1) {
      setIsEditingFromReview(false);
      setPhase('review');
      return;
    }
    navigateToQuestion(currentIndex + 1);
  }, [cancelAutoAdvance, currentIndex, flatQuestions.length, navigateToQuestion]);

  // Auto-advance helper for single_choice and scale
  const scheduleAutoAdvance = useCallback(
    (targetIndex: number, delayMs = 450) => {
      cancelAutoAdvance();
      setShowRequiredError(false);
      autoAdvanceTimerRef.current = setTimeout(() => {
        if (targetIndex >= flatQuestions.length) {
          setIsEditingFromReview(false);
          setPhase('review');
        } else {
          navigateToQuestion(targetIndex);
        }
      }, delayMs);
    },
    [cancelAutoAdvance, flatQuestions.length, navigateToQuestion]
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

      const curr = (answers[q.id] as string[]) || [];

      if (curr.includes(optId)) {
        // Deselect
        const next = curr.filter((id) => id !== optId);
        setAnswer(q.id, next);
      } else {
        // If max_select is enforced and limit reached, do not add
        if (q.max_select && curr.length >= q.max_select) {
          return;
        }
        const next = [...curr, optId];
        setAnswer(q.id, next);
      }
    },
    [flatQuestions, currentIndex, answers, setAnswer]
  );

  // Jump from review to edit a question
  const handleEditFromReview = useCallback((targetIndex: number) => {
    setIsEditingFromReview(true);
    setCurrentIndex(targetIndex);
    setShowRequiredError(false);
    setSelectedSingleChoice(null);
    setPulseScaleValue(null);
    setPhase('question');
  }, []);

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

  // Submit assessment or intake handler
  const handleSubmit = async () => {
    if (!storeFamily?.code || !storeFamily?.token) return;

    if (saveDebounceTimerRef.current) {
      clearTimeout(saveDebounceTimerRef.current);
    }
    const pending = { ...unsavedAnswersRef.current };
    if (Object.keys(pending).length > 0) {
      try {
        await config.saveAnswers(storeFamily.code, storeFamily.token, pending);
        Object.keys(pending).forEach((k) => delete unsavedAnswersRef.current[k]);
      } catch {
        // Continue to submit which handles validation
      }
    }

    setPhase('submitting');
    setSubmitError(null);
    try {
      await config.submit(storeFamily.code, storeFamily.token);
      setPhase('done');
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === 'wrong_role') {
          router.replace(config.wrongRoleRedirect);
          return;
        }
        if (
          (err.code === 'assessment_incomplete' || err.code === 'intake_incomplete') &&
          err.missing &&
          err.missing.length > 0
        ) {
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
        setSubmitError(err.message || 'Submission could not be completed. Please check your answers.');
      } else {
        setSubmitError(err instanceof Error ? err.message : 'Submission failed. Please try again.');
      }
      setPhase('review');
    }
  };

  // Poll status in done state every 2s
  useEffect(() => {
    if (phase !== 'done' || !storeFamily?.code || !storeFamily?.token) return;

    let mounted = true;
    const checkStatus = async () => {
      if (!isTabVisibleRef.current) return;
      try {
        const status = await getStatus(storeFamily.code, storeFamily.token);
        if (mounted && status.partner?.done) {
          setIsPartnerDone(true);
        }
      } catch {
        // Ignore poll failures
      }
    };

    checkStatus();
    const timer = setInterval(checkStatus, 2000);

    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, [phase, storeFamily]);

  // Current question data
  const currentQ = flatQuestions[currentIndex];
  const sectionInfo = currentQ ? questionToSectionMap.get(currentQ.id) : null;
  const currentAnswer = currentQ ? answers[currentQ.id] : undefined;

  // Calculate section progress counts for rail and review
  const sectionStats = useMemo(() => {
    return sections.map((sec, secIdx) => {
      const startIndex = sections
        .slice(0, secIdx)
        .reduce((sum, s) => sum + s.questions.length, 0);
      const total = sec.questions.length;
      const answered = sec.questions.filter((q) => isQuestionAnswered(q, answers[q.id])).length;
      return {
        section: sec,
        total,
        answered,
        startIndex,
      };
    });
  }, [sections, answers]);

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
                  {getLocalizedText(interstitialInfo.prevSectionTitle, storeLang)}
                </h2>
                <p className="text-base text-midnight/70 font-normal">
                  {getLocalizedText(interstitialInfo.nextSectionTitle, storeLang)}
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
                  <div className="flex items-center gap-2">
                    <span>{sectionInfo ? getLocalizedText(sectionInfo.section.title, storeLang) : ''}</span>
                    {isEditingFromReview && (
                      <button
                        type="button"
                        onClick={handleReturnToReview}
                        className="text-[11px] font-semibold text-ocean hover:underline px-2 py-0.5 rounded bg-ocean/10 transition-colors cursor-pointer"
                      >
                        {t.backToReview} →
                      </button>
                    )}
                  </div>
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

                {/* Stepper progress rail proportional to section question counts */}
                <div
                  className="flex gap-1.5 h-1.5 w-full"
                  role="progressbar"
                  aria-label="Progress rail"
                  aria-valuenow={currentIndex + 1}
                  aria-valuemin={1}
                  aria-valuemax={flatQuestions.length || 1}
                >
                  {sectionStats.map((stat, idx) => {
                    const isPassed = currentIndex > stat.startIndex + stat.total - 1;
                    const isCurrent =
                      currentIndex >= stat.startIndex && currentIndex < stat.startIndex + stat.total;
                    const fillPercent = isPassed
                      ? 100
                      : isCurrent
                      ? ((currentIndex - stat.startIndex + 1) / Math.max(stat.total, 1)) * 100
                      : 0;

                    return (
                      <div
                        key={stat.section.id || idx}
                        className="h-full bg-cloud rounded-full overflow-hidden"
                        style={{ flex: Math.max(stat.total, 1) }}
                        title={getLocalizedText(stat.section.title, storeLang)}
                        aria-label={`Step ${idx + 1} of ${sections.length}: ${getLocalizedText(stat.section.title, storeLang)}`}
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

              {/* Animated Question Container */}
              <div className="flex-1 flex flex-col justify-between">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={currentQ.id}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -16 }}
                    transition={{ duration: 0.25, ease: 'easeOut' }}
                    className="space-y-6 flex-1 flex flex-col justify-between"
                  >
                    <div className="space-y-3">
                      <motion.h2
                        className={`${headingFontClass} text-xl sm:text-2xl font-bold text-midnight tracking-tight`}
                      >
                        {getLocalizedText(currentQ.prompt, storeLang)}
                      </motion.h2>

                      {/* On the very first question only: quiet privacy text for parent intake */}
                      {config.showPrivacyIntakeOnFirstQuestion && currentIndex === 0 && (
                        <p className="text-xs sm:text-sm text-midnight/65 font-normal">
                          {t.privacyIntake}
                        </p>
                      )}

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
                              selectedSingleChoice !== null
                                ? selectedSingleChoice === opt.id
                                : currentAnswer === opt.id;
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
                              {
                                length:
                                  (currentQ.max ?? 5) - (currentQ.min ?? 1) + 1,
                              },
                              (_, i) => (currentQ.min ?? 1) + i
                            ).map((val) => {
                              const isSelected = currentAnswer === val;
                              const isPulsing = pulseScaleValue === val;

                              return (
                                <motion.button
                                  key={val}
                                  type="button"
                                  onClick={() => handleSelectScale(val)}
                                  animate={isPulsing ? { scale: [1, 1.15, 1] } : {}}
                                  transition={{ duration: 0.3 }}
                                  className={`w-12 h-12 sm:w-14 sm:h-14 rounded-full border-2 font-mono text-base sm:text-lg font-bold flex items-center justify-center transition-colors cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ocean ${
                                    isSelected
                                      ? 'bg-ocean border-ocean text-white shadow-md'
                                      : 'bg-white border-cloud text-midnight hover:border-sky'
                                  }`}
                                >
                                  {val}
                                </motion.button>
                              );
                            })}
                          </div>

                          <div className="flex justify-between text-xs sm:text-sm text-midnight/70 max-w-md mx-auto">
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

                            {/* Native Range Slider */}
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

                      {/* TYPE 4: MULTI CHOICE (Supports max_select) */}
                      {currentQ.type === 'multi_choice' && currentQ.options && (
                        <div className="space-y-3">
                          {/* Quiet max_select hint under question once limit is reached */}
                          {currentQ.max_select &&
                            Array.isArray(currentAnswer) &&
                            currentAnswer.length >= currentQ.max_select && (
                              <p className="text-xs text-midnight/60 font-normal">
                                {t.maxSelectHint.replace('{n}', currentQ.max_select.toString())}
                              </p>
                            )}

                          {currentQ.options.map((opt, optIdx) => {
                            const selectedList = (currentAnswer as string[]) || [];
                            const isSelected = selectedList.includes(opt.id);
                            const isLimitReached =
                              !!currentQ.max_select && selectedList.length >= currentQ.max_select;
                            const isDimmed = isLimitReached && !isSelected;

                            return (
                              <motion.button
                                key={opt.id}
                                initial={{ y: 12, opacity: 0 }}
                                animate={{ y: 0, opacity: isDimmed ? 0.45 : 1 }}
                                transition={{
                                  duration: 0.25,
                                  delay: optIdx * 0.04,
                                  ease: 'easeOut',
                                }}
                                type="button"
                                disabled={isDimmed}
                                onClick={() => handleToggleMultiChoice(opt.id)}
                                className={`w-full min-h-[52px] p-3.5 sm:p-4 rounded-xl border-2 flex items-center justify-between transition-colors text-left ${
                                  isDimmed
                                    ? 'bg-cloud/40 border-cloud/60 text-midnight/40 cursor-not-allowed pointer-events-none'
                                    : isSelected
                                    ? 'bg-sky-tint border-ocean text-midnight cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ocean'
                                    : 'bg-white border-cloud hover:border-sky/70 text-midnight cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ocean'
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
                            {((currentAnswer as string) || '').length} /{' '}
                            {currentQ.max_length ?? 300}
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
                        ) : isEditingFromReview ? (
                          <button
                            type="button"
                            onClick={handleReturnToReview}
                            className="px-4 py-2 text-sm font-medium text-midnight/70 hover:text-midnight rounded-lg transition-colors focus-visible:outline-2 focus-visible:outline-ocean cursor-pointer"
                          >
                            ← {t.backToReview}
                          </button>
                        ) : (
                          <div />
                        )}
                      </div>

                      <div className="flex items-center gap-3">
                        {isEditingFromReview && (
                          <button
                            type="button"
                            onClick={handleReturnToReview}
                            className="px-4 py-2 text-sm font-semibold text-ocean hover:bg-ocean/10 rounded-xl transition-colors focus-visible:outline-2 focus-visible:outline-ocean cursor-pointer"
                          >
                            {t.backToReview}
                          </button>
                        )}

                        {!currentQ.required && (
                          <button
                            type="button"
                            onClick={handleSkip}
                            className="px-4 py-2 text-sm font-medium text-midnight/60 hover:text-midnight rounded-lg transition-colors focus-visible:outline-2 focus-visible:outline-ocean cursor-pointer"
                          >
                            {t.skip}
                          </button>
                        )}

                        {/* Continue Button for types that don't auto-advance or after manual edit */}
                        {(isEditingFromReview ||
                          currentQ.type === 'multi_choice' ||
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
          {/* PHASE: REVIEW / CONFIRMATION SCREEN                      */}
          {/* ======================================================== */}
          {(phase === 'review' || phase === 'submitting') && (
            <div className="flex-1 flex flex-col justify-between space-y-8">
              {/* STUDENT REVIEW SCREEN */}
              {config.reviewType === 'student' ? (
                <>
                  <div className="space-y-6">
                    <div className="space-y-2">
                      <h2
                        className={`${headingFontClass} text-2xl sm:text-3xl font-bold text-midnight tracking-tight`}
                      >
                        {t.reviewTitle}
                      </h2>
                      <p className="text-sm sm:text-base text-midnight/70">
                        {t.reviewBody}
                      </p>
                    </div>

                    {/* Section Summary & Question Rows */}
                    <div className="space-y-4">
                      {sectionStats.map((stat) => {
                        const isAllDone = stat.answered === stat.total;

                        return (
                          <div
                            key={stat.section.id}
                            className="bg-white border-2 border-cloud rounded-xl p-4 sm:p-5 space-y-3"
                          >
                            <div className="flex items-center justify-between">
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
                                <button
                                  type="button"
                                  onClick={() => handleEditFromReview(stat.startIndex)}
                                  className="text-sm font-semibold text-ocean hover:underline px-2 py-1 rounded cursor-pointer"
                                >
                                  {t.edit} →
                                </button>
                              </div>
                            </div>

                            {/* Individual questions in this section */}
                            <div className="pt-2 border-t border-cloud/60 divide-y divide-cloud/60">
                              {stat.section.questions.map((q) => {
                                const flatIdx = flatQuestions.findIndex((item) => item.id === q.id);
                                const rawVal = answers[q.id];
                                const hasAnswer =
                                  rawVal !== undefined &&
                                  rawVal !== null &&
                                  rawVal !== '' &&
                                  !(Array.isArray(rawVal) && rawVal.length === 0);
                                const answerDisplay = formatAnswerText(
                                  q,
                                  rawVal,
                                  storeLang,
                                  t.skippedAnswer
                                );

                                return (
                                  <div
                                    key={q.id}
                                    className="py-2.5 flex items-start justify-between gap-3"
                                  >
                                    <div className="space-y-0.5 flex-1 min-w-0">
                                      <p className="text-xs sm:text-sm font-medium text-midnight leading-snug">
                                        {getLocalizedText(q.prompt, storeLang)}
                                      </p>
                                      <p
                                        className={`text-xs ${
                                          hasAnswer
                                            ? 'text-ocean font-medium'
                                            : 'text-midnight/45 italic font-normal'
                                        }`}
                                      >
                                        {answerDisplay}
                                      </p>
                                    </div>

                                    <button
                                      type="button"
                                      onClick={() => handleEditFromReview(flatIdx)}
                                      className="text-xs font-semibold text-ocean hover:underline px-2 py-1 rounded shrink-0 cursor-pointer"
                                    >
                                      {t.edit}
                                    </button>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="pt-4 border-t border-cloud/70">
                    {submitError && (
                      <p role="alert" className="text-xs sm:text-sm text-red-600 font-medium mb-3 text-center">
                        {submitError}
                      </p>
                    )}
                    <button
                      type="button"
                      disabled={phase === 'submitting'}
                      onClick={handleSubmit}
                      className="w-full py-3.5 px-6 bg-ocean text-white font-semibold text-base rounded-xl hover:bg-[#255ba0] transition-colors focus-visible:outline-2 focus-visible:outline-ocean cursor-pointer"
                    >
                      {phase === 'submitting' ? t.submitting : t.submit}
                    </button>
                  </div>
                </>
              ) : (
                /* PARENT CONFIRMATION SCREEN */
                <>
                  <div className="space-y-8">
                    <div className="space-y-2">
                      <h2
                        className={`${headingFontClass} text-2xl sm:text-3xl font-bold text-midnight tracking-tight`}
                      >
                        {t.intakeReviewTitle}
                      </h2>
                      <p className="text-sm sm:text-base text-midnight/70">
                        {t.intakeReviewBody}
                      </p>
                    </div>

                    {/* Section blocks with plain rows separated by thin cloud-colored lines */}
                    <div className="space-y-8">
                      {sections.map((sec) => (
                        <div key={sec.id} className="space-y-3">
                          <h3
                            className={`${headingFontClass} text-base sm:text-lg font-bold text-midnight pb-2 border-b-2 border-cloud`}
                          >
                            {getLocalizedText(sec.title, storeLang)}
                          </h3>

                          <div className="divide-y divide-cloud/80">
                            {sec.questions.map((q) => {
                              const flatIdx = flatQuestions.findIndex((item) => item.id === q.id);
                              const rawVal = answers[q.id];
                              const hasAnswer =
                                rawVal !== undefined &&
                                rawVal !== null &&
                                rawVal !== '' &&
                                !(Array.isArray(rawVal) && rawVal.length === 0);
                              const answerDisplay = formatAnswerText(
                                q,
                                rawVal,
                                storeLang,
                                t.skippedAnswer
                              );

                              return (
                                <div
                                  key={q.id}
                                  className="py-3.5 flex items-start justify-between gap-4"
                                >
                                  <div className="space-y-1 flex-1 min-w-0">
                                    <p className="text-sm font-medium text-midnight leading-snug">
                                      {getLocalizedText(q.prompt, storeLang)}
                                    </p>
                                    <p
                                      className={`text-sm ${
                                        hasAnswer
                                          ? 'text-ocean font-medium'
                                          : 'text-midnight/45 italic font-normal'
                                      }`}
                                    >
                                      {answerDisplay}
                                    </p>
                                  </div>

                                  <button
                                    type="button"
                                    onClick={() => handleEditFromReview(flatIdx)}
                                    className="text-xs sm:text-sm font-semibold text-ocean hover:underline px-2 py-1 rounded focus-visible:outline-2 focus-visible:outline-ocean cursor-pointer shrink-0"
                                  >
                                    {t.edit}
                                  </button>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="pt-6 border-t border-cloud/70">
                    {submitError && (
                      <p role="alert" className="text-xs sm:text-sm text-red-600 font-medium mb-3 text-center">
                        {submitError}
                      </p>
                    )}
                    <button
                      type="button"
                      disabled={phase === 'submitting'}
                      onClick={handleSubmit}
                      className="w-full py-3.5 px-6 bg-ocean text-white font-semibold text-base rounded-xl hover:bg-[#255ba0] transition-colors focus-visible:outline-2 focus-visible:outline-ocean cursor-pointer"
                    >
                      {phase === 'submitting' ? t.submitting : t.confirmSubmit}
                    </button>
                  </div>
                </>
              )}
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
                <h2
                  className={`${headingFontClass} text-2xl sm:text-3xl font-bold text-midnight tracking-tight`}
                >
                  {t.doneTitle.replace('{name}', storeName || t[config.role])}
                </h2>

                <p className="text-base text-midnight/70">
                  {isPartnerDone ? t.bothDone : t[config.partnerWaitingTextKey]}
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
                <div className="flex items-center gap-2 text-xs text-midnight/55 font-medium pt-2">
                  <span className="w-2 h-2 rounded-full bg-ocean animate-pulse" />
                  <span>...</span>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </MotionConfig>
  );
}

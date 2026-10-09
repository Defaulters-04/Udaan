'use client';

import React, { useState, useEffect, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useSessionStore, type Role } from '@/store/session';
import { getTranslation, type Language } from '@/lib/i18n';
import { PageShell } from '@/components/PageShell';
import { previewFamily, joinFamily, ApiError } from '@/lib/api';

function WelcomeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const codeParam = searchParams.get('code');
  const inviteCode = codeParam ? codeParam.trim().toUpperCase().replace(/[\s-]/g, '') : null;

  // Zustand store
  const storeRole = useSessionStore((state) => state.role);
  const storeName = useSessionStore((state) => state.name);
  const storeLang = useSessionStore((state) => state.lang);
  const storeLangChosen = useSessionStore((state) => state.langChosen);
  const setRole = useSessionStore((state) => state.setRole);
  const setName = useSessionStore((state) => state.setName);
  const setLang = useSessionStore((state) => state.setLang);
  const setFamily = useSessionStore((state) => state.setFamily);

  // Local editing states
  const [isStep1Editing, setIsStep1Editing] = useState(false);
  const [isStep2Editing, setIsStep2Editing] = useState(false);
  const [nameInput, setNameInput] = useState('');
  const [pendingRole, setPendingRole] = useState<Role | null>(null);

  // Invite state (loading is initialized to true if inviteCode exists)
  const [inviteState, setInviteState] = useState<{
    loading: boolean;
    error: string | null;
    creatorName: string | null;
  }>({
    loading: !!inviteCode,
    error: null,
    creatorName: null,
  });

  // DOM Refs for accessibility and smooth scrolling
  const step2Ref = useRef<HTMLDivElement>(null);
  const step3Ref = useRef<HTMLDivElement>(null);
  const nameInputRef = useRef<HTMLInputElement>(null);
  const announcementRef = useRef<HTMLDivElement>(null);

  // Rehydrate store on mount (per CONTEXT.md skipHydration requirement)
  useEffect(() => {
    useSessionStore.persist.rehydrate();
  }, []);

  // Sync document language attribute
  useEffect(() => {
    document.documentElement.lang = storeLang;
  }, [storeLang]);

  const t = getTranslation(storeLang);

  // Preview family if inviteCode is present
  useEffect(() => {
    if (!inviteCode) return;
    let active = true;

    previewFamily(inviteCode)
      .then((res) => {
        if (!active) return;
        if (!res.open_role) {
          setInviteState({ loading: false, error: t.errFull, creatorName: null });
          return;
        }
        setInviteState({ loading: false, error: null, creatorName: res.creator_name });
        setRole(res.open_role);
        setIsStep1Editing(false);
        setIsStep2Editing(true);
        setTimeout(() => {
          nameInputRef.current?.focus();
        }, 100);
      })
      .catch((err) => {
        if (!active) return;
        const errMsg =
          err instanceof ApiError && err.code === 'family_not_found'
            ? t.errNotFound
            : t.errNetwork;
        setInviteState({ loading: false, error: errMsg, creatorName: null });
      });

    return () => {
      active = false;
    };
  }, [inviteCode, setRole, t.errFull, t.errNotFound, t.errNetwork]);

  // Helper for scroll into view respecting reduced motion
  const scrollTo = (el: HTMLElement | null) => {
    if (!el) return;
    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    el.scrollIntoView({
      behavior: prefersReducedMotion ? 'auto' : 'smooth',
      block: 'nearest',
    });
  };

  // Announce for screen readers
  const announce = (message: string) => {
    if (announcementRef.current) {
      announcementRef.current.textContent = message;
    }
  };

  // Step 1: Select Role
  const handleSelectRole = (role: Role) => {
    setPendingRole(role);
    setRole(role);
    announce(`${t.roleQuestion}: ${t[role]}`);

    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const delay = prefersReducedMotion ? 0 : 350;

    setTimeout(() => {
      setIsStep1Editing(false);
      setPendingRole(null);

      if (!storeName) {
        setIsStep2Editing(true);
        setTimeout(() => {
          scrollTo(step2Ref.current);
          nameInputRef.current?.focus();
        }, 50);
      }
    }, delay);
  };

  // Step 2: Name input submission
  const handleNameSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = nameInput.trim();
    if (!trimmed || trimmed.length > 40) return;

    setName(trimmed);
    setIsStep2Editing(false);
    announce(t.greeting.replace('{name}', trimmed));

    // Reveal step 3 and scroll
    setTimeout(() => {
      scrollTo(step3Ref.current);
    }, 50);
  };

  // Step 3: Choose Language
  const handleSelectLanguage = (lang: Language) => {
    setLang(lang);
    announce(`${t.langQuestion}: ${lang === 'hi' ? 'हिन्दी' : 'English'}`);
  };

  // Step 3: Proceed to /link
  const handleBegin = async () => {
    if (inviteCode && storeRole && storeName) {
      try {
        const res = await joinFamily(inviteCode, {
          role: storeRole,
          name: storeName,
          lang: storeLang,
        });
        setFamily({
          code: res.family_code,
          token: res.member_token,
          partner: res.partner,
        });
        router.push('/link');
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.code === 'role_taken') alert(t.errRoleTaken);
          else if (err.code === 'family_full') alert(t.errFull);
          else alert(t.errNetwork);
        } else {
          alert(t.errNetwork);
        }
      }
    } else {
      router.push('/link');
    }
  };

  const headingFontClass =
    storeLang === 'hi' ? 'font-hind' : 'font-bricolage';

  const effectiveRole = pendingRole || storeRole;
  const isStep1Answered = !!storeRole && !isStep1Editing;
  const isStep2Revealed = !!storeRole || !!pendingRole;
  const isStep2Answered = !!storeName && !isStep2Editing;
  const isStep3Revealed = !!storeRole && !!storeName && !isStep2Editing;

  return (
    <PageShell
      width="narrow"
      variant="hero"
      tagline={t.tagline}
      footer={
        <footer className="mt-14 sm:mt-20 pt-6 border-t border-cloud/70 text-xs sm:text-sm text-midnight/65 leading-relaxed">
          <p>{t.consent}</p>
        </footer>
      }
    >
      {/* Screen reader live announcement */}
      <div
        ref={announcementRef}
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      />

      <div className="pt-8 sm:pt-10 pb-12 flex-1 flex flex-col">

        {/* Invite Loading or Error */}
        {inviteState.loading && (
          <div className="mb-6 p-4 bg-cloud/50 rounded-xl flex items-center justify-center gap-3">
            <span className="w-4 h-4 border-2 border-cloud border-t-ocean rounded-full animate-spin" />
            <span className="text-sm text-midnight/80">Checking invite link…</span>
          </div>
        )}

        {inviteState.error && (
          <div className="mb-8 p-5 bg-white border-2 border-cloud rounded-xl space-y-4">
            <p role="alert" className="text-sm sm:text-base text-midnight">
              {inviteState.error}
            </p>
            <button
              type="button"
              onClick={() => {
                setInviteState({ loading: false, error: null, creatorName: null });
                router.replace('/');
              }}
              className="px-5 py-2.5 bg-ocean text-white text-sm font-semibold rounded-xl hover:bg-[#255ba0] focus-visible:outline-2 focus-visible:outline-ocean cursor-pointer"
            >
              {t.startNormally}
            </button>
          </div>
        )}

        {/* Valid Invite Banner */}
        {inviteState.creatorName && !inviteState.error && (
          <div className="mb-8 p-4 bg-cloud/70 rounded-xl border border-cloud">
            <p className="text-base font-medium text-midnight">
              {t.invited.replace('{name}', inviteState.creatorName)}
            </p>
          </div>
        )}

        {/* Flow Steps (hidden if invite error is blocking) */}
        {!inviteState.error && (
          <div className="space-y-8 sm:space-y-10 flex-1">
            {/* ================= STEP 1: ROLE ================= */}
            <section
              aria-labelledby="step-role-heading"
              onKeyDown={(e) => {
                if (
                  e.key === 'Escape' &&
                  isStep1Editing &&
                  storeRole &&
                  !inviteState.creatorName
                ) {
                  setIsStep1Editing(false);
                }
              }}
            >
              {isStep1Answered && storeRole ? (
                // Step 1: One-line summary (Without Change action if invite code used)
                <div className="flex items-center justify-between py-2.5 border-b border-cloud text-sm sm:text-base">
                  <div className="flex items-baseline gap-2 text-midnight">
                    <span className="text-midnight/60">{t.roleQuestion}</span>
                    <span className="font-semibold text-midnight">
                      {t[storeRole]}
                    </span>
                  </div>
                  {!inviteState.creatorName && (
                    <button
                      type="button"
                      onClick={() => setIsStep1Editing(true)}
                      className="text-ocean hover:underline font-medium text-sm px-2 py-1 rounded focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ocean cursor-pointer"
                    >
                      {t.change}
                    </button>
                  )}
                </div>
              ) : (
                // Step 1: Interactive selection buttons
                <div className="space-y-3.5">
                  <div className="flex items-center justify-between">
                    <h2
                      id="step-role-heading"
                      className={`${headingFontClass} text-lg sm:text-xl font-semibold text-midnight`}
                    >
                      {t.roleQuestion}
                    </h2>
                    {storeRole && isStep1Editing && !inviteState.creatorName && (
                      <button
                        type="button"
                        onClick={() => setIsStep1Editing(false)}
                        className="text-xs text-midnight/60 hover:text-midnight underline px-1 py-0.5 rounded focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ocean"
                      >
                        {storeLang === 'hi' ? 'रद्द करें' : 'Cancel'}
                      </button>
                    )}
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                    <button
                      type="button"
                      onClick={() => handleSelectRole('student')}
                      className={`text-left p-4 sm:p-5 rounded-xl border-2 transition-colors cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ocean ${
                        effectiveRole === 'student'
                          ? 'bg-sky-tint border-ocean text-midnight font-semibold'
                          : 'bg-white border-cloud hover:border-sky text-midnight'
                      }`}
                    >
                      <span className="block text-base sm:text-lg font-medium">
                        {t.student}
                      </span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleSelectRole('parent')}
                      className={`text-left p-4 sm:p-5 rounded-xl border-2 transition-colors cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ocean ${
                        effectiveRole === 'parent'
                          ? 'bg-sky-tint border-ocean text-midnight font-semibold'
                          : 'bg-white border-cloud hover:border-sky text-midnight'
                      }`}
                    >
                      <span className="block text-base sm:text-lg font-medium">
                        {t.parent}
                      </span>
                    </button>
                  </div>
                </div>
              )}
            </section>

            {/* ================= STEP 2: NAME ================= */}
            {isStep2Revealed && (
              <section
                ref={step2Ref}
                aria-labelledby="step-name-heading"
                onKeyDown={(e) => {
                  if (e.key === 'Escape' && isStep2Editing && storeName) {
                    setIsStep2Editing(false);
                  }
                }}
              >
                {isStep2Answered && storeName ? (
                  // Step 2: One-line answered summary (greeting with name)
                  <div className="flex items-center justify-between py-2.5 border-b border-cloud text-sm sm:text-base">
                    <div className="font-semibold text-midnight">
                      {t.greeting.replace('{name}', storeName)}
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setIsStep2Editing(true);
                        setNameInput(storeName);
                        setTimeout(() => nameInputRef.current?.focus(), 50);
                      }}
                      className="text-ocean hover:underline font-medium text-sm px-2 py-1 rounded focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ocean cursor-pointer"
                    >
                      {t.change}
                    </button>
                  </div>
                ) : (
                  // Step 2: Active input area with left-to-right wipe in place
                  <div className="wipe-reveal space-y-3.5">
                    <div className="flex items-center justify-between">
                      <h2
                        id="step-name-heading"
                        className={`${headingFontClass} text-lg sm:text-xl font-semibold text-midnight`}
                      >
                        <label htmlFor="user-name-input">{t.nameQuestion}</label>
                      </h2>
                      {storeName && isStep2Editing && (
                        <button
                          type="button"
                          onClick={() => setIsStep2Editing(false)}
                          className="text-xs text-midnight/60 hover:text-midnight underline px-1 py-0.5 rounded focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ocean"
                        >
                          {storeLang === 'hi' ? 'रद्द करें' : 'Cancel'}
                        </button>
                      )}
                    </div>
                    <form
                      onSubmit={handleNameSubmit}
                      className="flex flex-col sm:flex-row gap-3"
                    >
                      <input
                        ref={nameInputRef}
                        id="user-name-input"
                        type="text"
                        maxLength={40}
                        value={nameInput}
                        onChange={(e) => setNameInput(e.target.value)}
                        placeholder={t.namePlaceholder}
                        autoComplete="given-name"
                        className="flex-1 px-4 py-3 bg-white border-2 border-cloud rounded-xl text-midnight placeholder:text-midnight/40 text-base focus:border-ocean focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ocean transition-colors"
                      />
                      <button
                        type="submit"
                        disabled={
                          !nameInput.trim() || nameInput.trim().length > 40
                        }
                        className={`px-6 py-3 rounded-xl font-medium text-base transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ocean ${
                          nameInput.trim() && nameInput.trim().length <= 40
                            ? 'bg-ocean text-white hover:bg-[#255ba0] cursor-pointer'
                            : 'bg-cloud text-midnight/40 cursor-not-allowed'
                        }`}
                      >
                        {t.continue}
                      </button>
                    </form>
                  </div>
                )}
              </section>
            )}

            {/* ================= STEP 3: LANGUAGE ================= */}
            {isStep3Revealed && (
              <section
                ref={step3Ref}
                aria-labelledby="step-lang-heading"
                className="fade-in-reveal space-y-5"
              >
                <div className="space-y-3.5">
                  <h2
                    id="step-lang-heading"
                    className={`${headingFontClass} text-lg sm:text-xl font-semibold text-midnight`}
                  >
                    {t.langQuestion}
                  </h2>
                  <div className="grid grid-cols-2 gap-3 sm:gap-4">
                    <button
                      type="button"
                      onClick={() => handleSelectLanguage('en')}
                      className={`p-3.5 sm:p-4 rounded-xl border-2 text-center transition-colors cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ocean ${
                        storeLangChosen && storeLang === 'en'
                          ? 'bg-sky-tint border-ocean text-midnight font-semibold'
                          : 'bg-white border-cloud hover:border-sky text-midnight'
                      }`}
                    >
                      <span className="block text-base sm:text-lg font-medium">
                        English
                      </span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleSelectLanguage('hi')}
                      className={`p-3.5 sm:p-4 rounded-xl border-2 text-center transition-colors font-hind cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ocean ${
                        storeLangChosen && storeLang === 'hi'
                          ? 'bg-sky-tint border-ocean text-midnight font-semibold'
                          : 'bg-white border-cloud hover:border-sky text-midnight'
                      }`}
                    >
                      <span className="block text-base sm:text-lg font-medium">
                        हिन्दी
                      </span>
                    </button>
                  </div>
                </div>

                {/* Let's begin button */}
                {storeLangChosen && (
                  <div className="pt-2 fade-in-reveal">
                    <button
                      type="button"
                      onClick={handleBegin}
                      className="w-full sm:w-auto px-8 py-3.5 bg-ocean text-white font-semibold text-base rounded-xl hover:bg-[#255ba0] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ocean cursor-pointer"
                    >
                      {t.begin}
                    </button>
                  </div>
                )}
              </section>
            )}
          </div>
        )}
      </div>
    </PageShell>
  );
}

export default function WelcomePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-paper flex items-center justify-center">
          <div className="w-8 h-8 rounded-full border-2 border-cloud border-t-ocean animate-spin" />
        </div>
      }
    >
      <WelcomeContent />
    </Suspense>
  );
}

'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { QRCodeSVG } from 'qrcode.react';
import { useSessionStore } from '@/store/session';
import { getTranslation } from '@/lib/i18n';
import { Header } from '@/components/Header';
import {
  createFamily,
  getStatus,
  joinFamily,
  ApiError,
} from '@/lib/api';

export default function LinkFamilyPage() {
  const router = useRouter();

  // Session Store
  const storeRole = useSessionStore((state) => state.role);
  const storeName = useSessionStore((state) => state.name);
  const storeLang = useSessionStore((state) => state.lang);
  const storeFamily = useSessionStore((state) => state.family);
  const hasHydrated = useSessionStore((state) => state.hasHydrated);
  const setFamily = useSessionStore((state) => state.setFamily);
  const setPartner = useSessionStore((state) => state.setPartner);

  // Component state
  const [copied, setCopied] = useState(false);
  const [joinCodeInput, setJoinCodeInput] = useState('');
  const [joinError, setJoinError] = useState<string | null>(null);
  const [isJoining, setIsJoining] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);

  // Polling ref to easily clear/manage interval
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isTabVisibleRef = useRef<boolean>(true);

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

  // Redirect if role or name missing after hydration
  useEffect(() => {
    if (hasHydrated) {
      if (!storeRole || !storeName) {
        router.replace('/');
      }
    }
  }, [hasHydrated, storeRole, storeName, router]);

  // Stop polling helper
  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  // Single poll check
  const pollStatus = useCallback(
    async (code: string, token: string) => {
      // Don't poll if tab is hidden
      if (!isTabVisibleRef.current) return;

      try {
        const res = await getStatus(code, token);
        if (res.linked && res.partner) {
          setPartner(res.partner);
          stopPolling();
        }
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 401 || err.status === 404) {
            // Token expired or family gone: re-create family
            stopPolling();
            if (storeRole && storeName) {
              try {
                const newFam = await createFamily({
                  role: storeRole,
                  name: storeName,
                  lang: storeLang,
                });
                setFamily({
                  code: newFam.family_code,
                  token: newFam.member_token,
                  partner: null,
                });
              } catch {
                // Ignore failure on recreate attempt
              }
            }
          }
        }
      }
    },
    [setPartner, stopPolling, storeRole, storeName, storeLang, setFamily]
  );

  // Tab visibility tracking
  useEffect(() => {
    const handleVisibilityChange = () => {
      const isVisible = document.visibilityState === 'visible';
      isTabVisibleRef.current = isVisible;
      if (isVisible && storeFamily?.code && storeFamily?.token && !storeFamily?.partner) {
        pollStatus(storeFamily.code, storeFamily.token);
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [storeFamily, pollStatus]);

  // Initialize or check family on mount
  useEffect(() => {
    if (!hasHydrated || !storeRole || !storeName) return;

    let isCancelled = false;

    async function initFamily() {
      setIsInitializing(true);

      // If family already exists in store, check with getStatus
      if (storeFamily && storeFamily.code && storeFamily.token) {
        // If already linked, no need to poll
        if (storeFamily.partner) {
          setIsInitializing(false);
          return;
        }

        try {
          const status = await getStatus(storeFamily.code, storeFamily.token);
          if (isCancelled) return;

          if (status.linked && status.partner) {
            setPartner(status.partner);
            setIsInitializing(false);
            return;
          }
        } catch (err) {
          if (isCancelled) return;
          if (err instanceof ApiError && (err.status === 401 || err.status === 404)) {
            // Create a new family if invalid or not found
            try {
              const res = await createFamily({
                role: storeRole!,
                name: storeName!,
                lang: storeLang,
              });
              if (!isCancelled) {
                setFamily({
                  code: res.family_code,
                  token: res.member_token,
                  partner: null,
                });
              }
            } catch {
              // Ignore creation error
            }
          }
        }
      } else {
        // No family in store: create new family
        try {
          const res = await createFamily({
            role: storeRole!,
            name: storeName!,
            lang: storeLang,
          });
          if (!isCancelled) {
            setFamily({
              code: res.family_code,
              token: res.member_token,
              partner: null,
            });
          }
        } catch {
          // Ignore creation error
        }
      }

      if (!isCancelled) {
        setIsInitializing(false);
      }
    }

    initFamily();

    return () => {
      isCancelled = true;
      stopPolling();
    };
  }, [hasHydrated, storeRole, storeName, storeLang, storeFamily, setFamily, setPartner, stopPolling]);

  // Start polling when family exists and partner is not linked
  useEffect(() => {
    if (!storeFamily || !storeFamily.code || !storeFamily.token || storeFamily.partner) {
      stopPolling();
      return;
    }

    stopPolling();
    const code = storeFamily.code;
    const token = storeFamily.token;

    pollTimerRef.current = setInterval(() => {
      pollStatus(code, token);
    }, 2000);

    return () => {
      stopPolling();
    };
  }, [storeFamily, pollStatus, stopPolling]);

  // Copy code handler
  const handleCopyCode = async () => {
    if (!storeFamily?.code) return;
    try {
      await navigator.clipboard.writeText(storeFamily.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  // Join code input sanitizer (uppercase, strip spaces & hyphens, max 6)
  const handleJoinInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.toUpperCase().replace(/[\s-]/g, '');
    if (raw.length <= 6) {
      setJoinCodeInput(raw);
      setJoinError(null);
    }
  };

  // Join family with code handler
  const handleJoinSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = joinCodeInput.trim();
    if (clean.length !== 6 || !storeRole || !storeName) return;

    setIsJoining(true);
    setJoinError(null);

    try {
      const res = await joinFamily(clean, {
        role: storeRole,
        name: storeName,
        lang: storeLang,
      });

      // Stop previous polling and store new family
      stopPolling();
      setFamily({
        code: res.family_code,
        token: res.member_token,
        partner: res.partner,
      });
      setJoinCodeInput('');
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === 'family_not_found') {
          setJoinError(t.errNotFound);
        } else if (err.code === 'role_taken') {
          setJoinError(t.errRoleTaken);
        } else if (err.code === 'family_full') {
          setJoinError(t.errFull);
        } else if (err.code === 'network_error') {
          setJoinError(t.errNetwork);
        } else {
          setJoinError(err.message || t.errNetwork);
        }
      } else {
        setJoinError(t.errNetwork);
      }
    } finally {
      setIsJoining(false);
    }
  };

  // Continue button destination
  const handleContinue = () => {
    if (storeRole === 'student') {
      router.push('/assessment');
    } else {
      router.push('/intake');
    }
  };

  if (!hasHydrated || !storeRole || !storeName) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-cloud border-t-ocean animate-spin" />
      </div>
    );
  }

  // App URL for QR code
  const appBaseUrl =
    process.env.NEXT_PUBLIC_APP_URL ||
    (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000');
  const familyCode = storeFamily?.code || '';
  const qrLink = familyCode ? `${appBaseUrl}/?code=${encodeURIComponent(familyCode)}` : '';

  // Partner wording
  const partnerRoleWord =
    storeRole === 'student' ? t.partnerParent : t.partnerStudent;
  const isLinked = !!storeFamily?.partner;
  const partnerName = storeFamily?.partner?.name || '';

  return (
    <div className="min-h-screen bg-paper text-midnight selection:bg-sky/20 flex flex-col justify-between">
      {/* Centered single column, max 480px per design spec */}
      <main className="w-full max-w-[480px] mx-auto px-5 sm:px-6 pt-8 sm:pt-14 pb-12 flex-1 flex flex-col text-left">
        {/* Shared Udaan Header */}
        <Header backHref="/" backLabel={t.linkTitle} />

        <div className="space-y-8 flex-1">
          {/* Page Heading */}
          <div className="space-y-1.5">
            <h2
              className={`${headingFontClass} text-2xl sm:text-3xl font-bold text-midnight tracking-tight`}
            >
              {t.linkTitle}
            </h2>
          </div>

          {/* QR Code and Family Code Container */}
          <div className="flex flex-col items-center text-center space-y-6">
            {/* QR Tile */}
            <div className="bg-white p-4 sm:p-5 rounded-2xl border-2 border-cloud inline-flex items-center justify-center">
              {familyCode ? (
                <QRCodeSVG
                  value={qrLink}
                  size={220}
                  bgColor="#FFFFFF"
                  fgColor="#11284A"
                  level="M"
                  includeMargin={true}
                />
              ) : (
                <div className="w-[220px] h-[220px] flex items-center justify-center bg-cloud/30 rounded-xl">
                  <div className="w-6 h-6 border-2 border-cloud border-t-ocean rounded-full animate-spin" />
                </div>
              )}
            </div>

            {/* 6-Character Family Code */}
            <div className="w-full space-y-2">
              <span className="text-xs uppercase tracking-wider font-semibold text-midnight/60 block">
                {t.codeLabel}
              </span>
              <div className="flex items-center justify-center gap-3">
                <span className="font-mono text-3xl sm:text-4xl font-extrabold tracking-widest text-midnight select-all">
                  {familyCode || '------'}
                </span>
                <button
                  type="button"
                  onClick={handleCopyCode}
                  disabled={!familyCode}
                  className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-cloud hover:bg-cloud/80 text-midnight transition-colors focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ocean cursor-pointer"
                >
                  {copied ? t.copied : t.copyCode}
                </button>
              </div>
            </div>

            {/* Instructions */}
            <div className="space-y-2 max-w-sm text-center">
              <p className="text-sm sm:text-base text-midnight/85 leading-relaxed font-normal">
                {storeRole === 'student' ? t.instrToParent : t.instrToStudent}
              </p>
              <p className="text-xs text-midnight/60 font-normal">
                {t.privacyNote}
              </p>
            </div>

            {/* Status Line with aria-live */}
            <div
              aria-live="polite"
              aria-atomic="true"
              className="w-full p-4 rounded-xl border-2 transition-all text-center"
              style={{
                backgroundColor: isLinked ? 'rgba(125, 190, 240, 0.15)' : '#E3EEF8',
                borderColor: isLinked ? '#2D6FB8' : '#E3EEF8',
              }}
            >
              {isInitializing && !familyCode ? (
                <span className="text-sm text-midnight/70">…</span>
              ) : isLinked ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-ocean" />
                    <span className="font-semibold text-base sm:text-lg text-midnight">
                      {t.connected.replace('{name}', partnerName)}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={handleContinue}
                    className="w-full py-3 px-6 bg-ocean text-white font-semibold text-base rounded-xl hover:bg-[#255ba0] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ocean cursor-pointer"
                  >
                    {t.continue}
                  </button>
                </div>
              ) : (
                <div className="flex items-center justify-center gap-2.5 py-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-ocean animate-pulse" />
                  <span className="text-sm sm:text-base font-medium text-midnight/90">
                    {t.waiting.replace('{partner}', partnerRoleWord)}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* "Already have a code?" Section */}
          {!isLinked && (
            <section
              aria-labelledby="join-code-heading"
              className="pt-6 border-t border-cloud space-y-4"
            >
              <h3
                id="join-code-heading"
                className="text-base sm:text-lg font-semibold text-midnight"
              >
                {t.haveCode}
              </h3>
              <form onSubmit={handleJoinSubmit} className="space-y-3">
                <div className="flex gap-2.5">
                  <input
                    type="text"
                    maxLength={6}
                    value={joinCodeInput}
                    onChange={handleJoinInputChange}
                    placeholder={t.codePlaceholder}
                    autoCapitalize="characters"
                    autoCorrect="off"
                    spellCheck="false"
                    className="flex-1 px-4 py-2.5 bg-white border-2 border-cloud rounded-xl font-mono text-base tracking-widest text-midnight placeholder:text-midnight/40 placeholder:font-sans placeholder:tracking-normal focus:border-ocean focus-visible:outline-2 focus-visible:outline-ocean transition-colors uppercase"
                  />
                  <button
                    type="submit"
                    disabled={joinCodeInput.length !== 6 || isJoining}
                    className={`px-5 py-2.5 rounded-xl font-semibold text-sm sm:text-base transition-colors focus-visible:outline-2 focus-visible:outline-ocean ${
                      joinCodeInput.length === 6 && !isJoining
                        ? 'bg-ocean text-white hover:bg-[#255ba0] cursor-pointer'
                        : 'bg-cloud text-midnight/40 cursor-not-allowed'
                    }`}
                  >
                    {isJoining ? t.joining : t.join}
                  </button>
                </div>

                {/* Inline Error Message */}
                {joinError && (
                  <p
                    role="alert"
                    className="text-xs sm:text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-2.5 leading-snug"
                  >
                    {joinError}
                  </p>
                )}
              </form>
            </section>
          )}
        </div>

        {/* Consent Footnote */}
        <footer className="mt-14 sm:mt-16 pt-6 border-t border-cloud/70 text-xs sm:text-sm text-midnight/65 leading-relaxed">
          <p>{t.consent}</p>
        </footer>
      </main>
    </div>
  );
}

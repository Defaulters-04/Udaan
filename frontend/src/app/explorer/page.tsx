'use client';

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { useSessionStore } from '@/store/session';
import { getTranslation } from '@/lib/i18n';
import { Header } from '@/components/Header';
import {
  getExplorer,
  getStatus,
  ApiError,
  isMockEnabled,
  validateExplorerResponse,
  type ExplorerResponse,
  type ExplorerCareer,
} from '@/lib/api';

// Single number formatter (Rule A2) used everywhere
const fmt = (n: number | null | undefined): string => {
  if (n === null || n === undefined) return '';
  return Math.round(n).toString();
};

export default function NegotiationExplorerPage() {
  const router = useRouter();
  const shouldReduceMotion = useReducedMotion();

  // Session Store
  const storeRole = useSessionStore((state) => state.role);
  const storeName = useSessionStore((state) => state.name);
  const storeLang = useSessionStore((state) => state.lang);
  const storeFamily = useSessionStore((state) => state.family);
  const hasHydrated = useSessionStore((state) => state.hasHydrated);

  // Component State only (Never in Zustand/storage per contract)
  const [data, setData] = useState<ExplorerResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [isWaitingPartner, setIsWaitingPartner] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Explorer interactive state
  const [sliderPos, setSliderPos] = useState<number>(50);
  const [selectedCareerId, setSelectedCareerId] = useState<string | null>(null);
  const [hoveredCareerId, setHoveredCareerId] = useState<string | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<{
    career: ExplorerCareer;
    members: ExplorerCareer[];
    xPct: number;
    yPct: number;
  } | null>(null);
  const [activeDomains, setActiveDomains] = useState<Set<string>>(new Set());
  const [isZoomed, setIsZoomed] = useState<boolean>(true);
  const [showAllNonBlocked, setShowAllNonBlocked] = useState<boolean>(false);
  const [showNoRouteDataSection, setShowNoRouteDataSection] = useState<boolean>(false);
  const [expandedBlockedIds, setExpandedBlockedIds] = useState<Set<string>>(new Set());
  const [selectedGroupMembers, setSelectedGroupMembers] = useState<ExplorerCareer[] | null>(null);
  const [announcedLiveText, setAnnouncedLiveText] = useState<string>('');

  // Mobile bottom sheet focus management
  const lastFocusedTriggerRef = useRef<HTMLElement | null>(null);
  const detailPanelRef = useRef<HTMLDivElement | null>(null);

  // Polling ref for 409 waiting state
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isPollingRef = useRef(false);

  // Debounced announcement timer
  const announceTimerRef = useRef<NodeJS.Timeout | null>(null);

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

  // Names logic (Rule 3)
  const studentName = useMemo(() => {
    if (storeRole === 'student') {
      return storeName?.trim() || (storeLang === 'hi' ? 'विद्यार्थी' : 'Student');
    }
    return storeFamily?.partner?.name?.trim() || (storeLang === 'hi' ? 'विद्यार्थी' : 'Student');
  }, [storeRole, storeName, storeFamily, storeLang]);

  // Auth Guard: if no family or token, send to /
  useEffect(() => {
    if (!hasHydrated) return;
    if (!storeFamily || !storeFamily.code || !storeFamily.token) {
      router.replace('/');
    }
  }, [hasHydrated, storeFamily, router]);

  // Polling helper
  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    isPollingRef.current = false;
  }, []);

  // Fetch Explorer data
  const fetchExplorer = useCallback(async () => {
    if (!storeFamily || !storeFamily.code || !storeFamily.token) return;

    setLoading(true);
    setErrorMessage(null);

    try {
      const res = await getExplorer(storeFamily.code, storeFamily.token);

      // Validate response strictly on arrival (Rule A3 / V1)
      const validation = validateExplorerResponse(res);
      if (!validation.valid) {
        console.error(validation.brokenRule);
        setErrorMessage(t.explorerErrorTitle);
        setData(null);
        return;
      }

      setData(res);
      setSliderPos(res.slider.default);

      // Default selected career to rank 1 winner if available
      const defPos = res.slider.default;
      const posIdx = res.slider.positions.indexOf(defPos);
      const topPick = res.careers.find(
        (c) => c.blocked === null && c.blend && c.blend[posIdx]?.rank === 1
      );
      if (topPick) setSelectedCareerId(topPick.id);

      setIsWaitingPartner(false);
      stopPolling();
    } catch (err) {
      if (err instanceof ApiError && (err.code === 'explorer_not_ready' || err.status === 409)) {
        setIsWaitingPartner(true);
        setData(null);
      } else {
        setIsWaitingPartner(false);
        setErrorMessage(
          err instanceof ApiError ? err.message : t.explorerErrorTitle
        );
      }
    } finally {
      setLoading(false);
    }
  }, [storeFamily, stopPolling, t.explorerErrorTitle]);

  // Initial load
  useEffect(() => {
    if (!hasHydrated || !storeFamily?.code || !storeFamily?.token) return;

    let isMounted = true;

    const loadInitialData = async () => {
      try {
        const res = await getExplorer(storeFamily.code, storeFamily.token);
        if (!isMounted) return;

        const validation = validateExplorerResponse(res);
        if (!validation.valid) {
          console.error(validation.brokenRule);
          setErrorMessage(t.explorerErrorTitle);
          setData(null);
          setLoading(false);
          return;
        }

        setData(res);
        setSliderPos(res.slider.default);

        // Default selected career to rank 1 winner
        const defPos = res.slider.default;
        const posIdx = res.slider.positions.indexOf(defPos);
        const topPick = res.careers.find(
          (c) => c.blocked === null && c.blend && c.blend[posIdx]?.rank === 1
        );
        if (topPick) setSelectedCareerId(topPick.id);

        setIsWaitingPartner(false);
        setLoading(false);
      } catch (err) {
        if (!isMounted) return;
        if (err instanceof ApiError && (err.code === 'explorer_not_ready' || err.status === 409)) {
          setIsWaitingPartner(true);
          setData(null);
        } else {
          setIsWaitingPartner(false);
          setErrorMessage(
            err instanceof ApiError ? err.message : t.explorerErrorTitle
          );
        }
        setLoading(false);
      }
    };

    loadInitialData();

    return () => {
      isMounted = false;
    };
  }, [hasHydrated, storeFamily?.code, storeFamily?.token, t.explorerErrorTitle]);

  // Polling when partner not ready
  useEffect(() => {
    if (!isWaitingPartner || !storeFamily?.code || !storeFamily?.token) {
      stopPolling();
      return;
    }

    if (isPollingRef.current) return;
    isPollingRef.current = true;

    pollTimerRef.current = setInterval(async () => {
      try {
        const status = await getStatus(storeFamily.code, storeFamily.token);
        if (status.you?.done && status.partner?.done) {
          stopPolling();
          fetchExplorer();
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          stopPolling();
          router.replace('/');
        }
      }
    }, 2000);

    return () => {
      stopPolling();
    };
  }, [isWaitingPartner, storeFamily, stopPolling, fetchExplorer, router]);

  // Derived careers partitioning
  const nonBlockedCareers = useMemo(() => {
    if (!data) return [];
    return data.careers.filter((c) => c.blocked === null && c.blend !== null);
  }, [data]);

  const blockedCareers = useMemo(() => {
    if (!data) return [];
    return data.careers.filter((c) => c.blocked !== null);
  }, [data]);

  const costAndAcademicBlocked = useMemo(() => {
    return blockedCareers.filter((c) => c.blocked?.cause !== 'no_route_data');
  }, [blockedCareers]);

  const noRouteDataBlocked = useMemo(() => {
    return blockedCareers.filter((c) => c.blocked?.cause === 'no_route_data');
  }, [blockedCareers]);

  // Unique domains present in data (order preserved from data)
  const availableDomains = useMemo(() => {
    if (!data) return [];
    const seen = new Set<string>();
    const list: string[] = [];
    for (const c of data.careers) {
      if (c.domain && !seen.has(c.domain)) {
        seen.add(c.domain);
        list.push(c.domain);
      }
    }
    return list;
  }, [data]);

  // Current slider index
  const sliderIdx = useMemo(() => {
    if (!data) return 0;
    const idx = data.slider.positions.indexOf(sliderPos);
    return idx >= 0 ? idx : 0;
  }, [data, sliderPos]);

  // Ranked non-blocked careers at current slider position (Rule A1)
  const rankedNonBlocked = useMemo(() => {
    if (!data || nonBlockedCareers.length === 0) return [];
    return [...nonBlockedCareers].sort(
      (a, b) => a.blend![sliderIdx].rank - b.blend![sliderIdx].rank
    );
  }, [data, nonBlockedCareers, sliderIdx]);

  // Current rank 1 winner
  const currentWinner = useMemo(() => {
    return rankedNonBlocked.length > 0 ? rankedNonBlocked[0] : null;
  }, [rankedNonBlocked]);

  // Debounced live announcement (400ms)
  useEffect(() => {
    if (!currentWinner) return;

    if (announceTimerRef.current) {
      clearTimeout(announceTimerRef.current);
    }

    announceTimerRef.current = setTimeout(() => {
      const winnerName = currentWinner.name[storeLang] ?? currentWinner.name.en;
      const score = fmt(currentWinner.blend![sliderIdx].score);
      setAnnouncedLiveText(
        t.topPickAnnounced.replace('{career}', winnerName).replace('{score}', score)
      );
    }, 400);

    return () => {
      if (announceTimerRef.current) {
        clearTimeout(announceTimerRef.current);
      }
    };
  }, [currentWinner, sliderIdx, storeLang, t.topPickAnnounced]);

  // Winner strip runs calculation (Item 10)
  const winnerStripSegments = useMemo(() => {
    if (!data || nonBlockedCareers.length === 0) return [];
    const { positions } = data.slider;

    const winnersAtPos = positions.map((pos, pIdx) => {
      const best = [...nonBlockedCareers].sort(
        (a, b) => a.blend![pIdx].rank - b.blend![pIdx].rank
      )[0];
      return { pos, pIdx, career: best };
    });

    const segments: Array<{
      career: ExplorerCareer;
      startPos: number;
      endPos: number;
      length: number;
    }> = [];

    let current = winnersAtPos[0];
    let startPos = current.pos;
    let count = 1;

    for (let i = 1; i < winnersAtPos.length; i++) {
      const next = winnersAtPos[i];
      if (next.career.id === current.career.id) {
        count++;
      } else {
        segments.push({
          career: current.career,
          startPos,
          endPos: winnersAtPos[i - 1].pos,
          length: count,
        });
        current = next;
        startPos = next.pos;
        count = 1;
      }
    }

    segments.push({
      career: current.career,
      startPos,
      endPos: winnersAtPos[winnersAtPos.length - 1].pos,
      length: count,
    });

    return segments;
  }, [data, nonBlockedCareers]);

  // Axes Zoom Bounds (V2)
  const { plotMin, plotMax, isZoomPossible } = useMemo(() => {
    if (nonBlockedCareers.length === 0) {
      return { plotMin: 0, plotMax: 100, isZoomPossible: false };
    }

    const fits = nonBlockedCareers.map((c) => c.fit!).filter((v) => v !== null);
    const viabs = nonBlockedCareers.map((c) => c.viability!).filter((v) => v !== null);

    const minVal = Math.min(...fits, ...viabs);
    const maxVal = Math.max(...fits, ...viabs);

    const calcMin = Math.max(0, Math.floor((minVal - 5) / 5) * 5);
    const calcMax = Math.min(100, Math.ceil((maxVal + 5) / 5) * 5);

    // At least 20 wide
    let finalMin = calcMin;
    let finalMax = calcMax;
    if (finalMax - finalMin < 20) {
      const diff = 20 - (finalMax - finalMin);
      finalMin = Math.max(0, finalMin - Math.ceil(diff / 2));
      finalMax = Math.min(100, finalMin + 20);
    }

    const canZoom = finalMin > 0 || finalMax < 100;

    if (!isZoomed || !canZoom) {
      return { plotMin: 0, plotMax: 100, isZoomPossible: canZoom };
    }

    return { plotMin: finalMin, plotMax: finalMax, isZoomPossible: canZoom };
  }, [nonBlockedCareers, isZoomed]);

  // SVG Coordinates mapping
  // ViewBox: 0 0 560 500
  const xGutterCenter = 32;
  const xGutterDivider = 58;
  const xPlotLeft = 78;
  const xPlotRight = 525;
  const yPlotTop = 40;
  const yPlotBottom = 430;

  const toX = useCallback(
    (viability: number) => {
      const clamped = Math.max(plotMin, Math.min(plotMax, viability));
      return (
        xPlotLeft +
        ((clamped - plotMin) / (plotMax - plotMin)) * (xPlotRight - xPlotLeft)
      );
    },
    [plotMin, plotMax, xPlotLeft, xPlotRight]
  );

  const toY = useCallback(
    (fit: number) => {
      const clamped = Math.max(plotMin, Math.min(plotMax, fit));
      return (
        yPlotBottom -
        ((clamped - plotMin) / (plotMax - plotMin)) * (yPlotBottom - yPlotTop)
      );
    },
    [plotMin, plotMax, yPlotTop, yPlotBottom]
  );

  // Coincident dots grouping for non-blocked careers (V3)
  const coincidentGroups = useMemo(() => {
    const groupsMap = new Map<string, ExplorerCareer[]>();

    for (const c of nonBlockedCareers) {
      const key = `${c.viability}_${c.fit}`;
      if (!groupsMap.has(key)) {
        groupsMap.set(key, []);
      }
      groupsMap.get(key)!.push(c);
    }

    return Array.from(groupsMap.entries()).map(([key, members]) => {
      // Marker styling comes from best-ranked member at current position
      const bestRankMember = [...members].sort(
        (a, b) => a.blend![sliderIdx].rank - b.blend![sliderIdx].rank
      )[0];

      return {
        key,
        viability: bestRankMember.viability!,
        fit: bestRankMember.fit!,
        count: members.length,
        members,
        representative: bestRankMember,
        rank: bestRankMember.blend![sliderIdx].rank,
      };
    });
  }, [nonBlockedCareers, sliderIdx]);

  // Coincident blocked careers in gutter (V5)
  const gutterBlockedGroups = useMemo(() => {
    const groupsMap = new Map<string, ExplorerCareer[]>();

    for (const c of blockedCareers) {
      if (c.fit !== null) {
        const key = `${c.fit}_${c.blocked?.cause}`;
        if (!groupsMap.has(key)) {
          groupsMap.set(key, []);
        }
        groupsMap.get(key)!.push(c);
      }
    }

    return Array.from(groupsMap.entries()).map(([key, members]) => {
      return {
        key,
        fit: members[0].fit!,
        cause: members[0].blocked?.cause,
        count: members.length,
        members,
        representative: members[0],
      };
    });
  }, [blockedCareers]);

  // Stepped Pareto Frontier path (V4)
  const frontierPathD = useMemo(() => {
    if (!data || data.frontier.length < 2) return '';

    const frontierCareers = data.frontier
      .map((id) => nonBlockedCareers.find((c) => c.id === id))
      .filter((c): c is ExplorerCareer => c !== undefined && c.viability !== null && c.fit !== null);

    if (frontierCareers.length < 2) return '';

    // Stepped line: horizontal then vertical between consecutive frontier points
    let d = `M ${toX(frontierCareers[0].viability!)} ${toY(frontierCareers[0].fit!)}`;

    for (let i = 1; i < frontierCareers.length; i++) {
      const curr = frontierCareers[i];
      const prev = frontierCareers[i - 1];
      const midX = toX(curr.viability!);
      const midY = toY(prev.fit!);
      d += ` L ${midX} ${midY} L ${toX(curr.viability!)} ${toY(curr.fit!)}`;
    }

    return d;
  }, [data, nonBlockedCareers, toX, toY]);

  // Selected Career Object
  const selectedCareer = useMemo(() => {
    if (!selectedCareerId || !data) return null;
    return data.careers.find((c) => c.id === selectedCareerId) || null;
  }, [selectedCareerId, data]);

  // Keyboard accessibility: Escape closes detail panel
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && selectedCareerId !== null) {
        setSelectedCareerId(null);
        setSelectedGroupMembers(null);
        lastFocusedTriggerRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedCareerId]);

  // Humanize unknown data gap ID helper
  const getDataGapLabel = (gapId: string): string => {
    if (gapId === 'verified_route_costs') return t.gap_verified_route_costs;
    if (gapId === 'verified_entry_salary') return t.gap_verified_entry_salary;
    if (gapId === 'regional_hiring') return t.gap_regional_hiring;
    if (gapId === 'exam_pattern') return t.gap_exam_pattern;
    return gapId.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  };

  // Verified careers count (V8)
  const verifiedCareersCount = useMemo(() => {
    if (!data) return 0;
    return data.careers.filter((c) => c.data_gaps.length === 0).length;
  }, [data]);

  // Grid tick marks
  const tickValues = useMemo(() => {
    const count = 5;
    const step = (plotMax - plotMin) / (count - 1);
    return Array.from({ length: count }, (_, i) => Math.round(plotMin + i * step));
  }, [plotMin, plotMax]);

  // Render Waiting State (409)
  if (isWaitingPartner) {
    return (
      <div className="min-h-screen bg-paper text-midnight flex flex-col justify-between p-4 sm:p-6 lg:p-8">
        <div className="max-w-2xl mx-auto w-full">
          <Header
            tagline={t.explorerSubtitle.replace('{student}', studentName)}
            backHref="/mirror"
            backLabel={t.back}
          />
          <div
            role="status"
            aria-live="polite"
            className="bg-cloud/30 border border-cloud rounded-2xl p-6 sm:p-8 text-center space-y-4 my-8"
          >
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-cloud text-ocean mb-2">
              <span className="w-4 h-4 rounded-full bg-ocean animate-pulse" />
            </div>
            <h2 className={`text-xl sm:text-2xl font-bold text-midnight ${headingFontClass}`}>
              {t.explorerWaitingTitle}
            </h2>
            <p className="text-sm sm:text-base text-midnight/80 max-w-md mx-auto leading-relaxed">
              {t.explorerWaitingDesc}
            </p>
            <div className="inline-block px-3 py-1 bg-white border border-cloud rounded-full text-xs font-medium text-ocean">
              {t.explorerWaitingBadge}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Render Error State
  if (errorMessage) {
    return (
      <div className="min-h-screen bg-paper text-midnight flex flex-col justify-between p-4 sm:p-6 lg:p-8">
        <div className="max-w-xl mx-auto w-full">
          <Header
            tagline={t.explorerSubtitle.replace('{student}', studentName)}
            backHref="/mirror"
            backLabel={t.back}
          />
          <div
            role="alert"
            className="bg-cloud/30 border border-ocean/30 rounded-2xl p-6 sm:p-8 text-center space-y-4 my-8"
          >
            <h2 className={`text-lg sm:text-xl font-bold text-midnight ${headingFontClass}`}>
              {t.explorerErrorTitle}
            </h2>
            <p className="text-sm text-midnight/70">{t.explorerErrorDesc}</p>
            <button
              type="button"
              onClick={() => fetchExplorer()}
              className="mt-4 px-6 py-2.5 rounded-xl bg-ocean text-white font-medium text-sm hover:bg-ocean/90 focus-visible:outline-2 focus-visible:outline-ocean transition-all cursor-pointer"
            >
              {t.retry}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Render Loading Skeleton
  if (loading || !data) {
    return (
      <div className="min-h-screen bg-paper text-midnight flex flex-col justify-between p-4 sm:p-6 lg:p-8">
        <div className="max-w-5xl mx-auto w-full">
          <Header
            tagline={t.explorerSubtitle.replace('{student}', studentName)}
            backHref="/mirror"
            backLabel={t.back}
          />
          <div className="animate-pulse space-y-6 my-8">
            <div className="h-10 bg-cloud/40 rounded-xl w-3/4 mx-auto" />
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              <div className="lg:col-span-7 h-96 bg-cloud/30 rounded-2xl" />
              <div className="lg:col-span-5 h-96 bg-cloud/30 rounded-2xl" />
            </div>
            <div className="h-24 bg-cloud/30 rounded-2xl" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper text-midnight flex flex-col justify-between p-4 sm:p-6 lg:p-8 selection:bg-sky/40">
      {/* Screen Reader Live Region */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {announcedLiveText}
      </div>

      <div className="max-w-7xl mx-auto w-full">
        {/* Navigation Header */}
        <Header
          tagline={t.explorerSubtitle.replace('{student}', studentName)}
          backHref="/mirror"
          backLabel={t.back}
        />

        {/* Demo Data Label (when mock data is shown) */}
        {isMockEnabled() && (
          <div className="flex items-center gap-2 mt-2 mb-3">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-cloud text-midnight/80 border border-cloud">
              {t.demoData}
            </span>
          </div>
        )}

        {/* V6 Empty State: When no careers fit the budget */}
        {nonBlockedCareers.length === 0 ? (
          <div className="my-8 max-w-3xl mx-auto space-y-8">
            <div className="bg-white border border-cloud rounded-2xl p-6 sm:p-8 text-center space-y-3">
              <h2 className={`text-xl font-bold text-midnight ${headingFontClass}`}>
                {t.emptyStateTitle}
              </h2>
            </div>

            {/* Needs a Plan section for blocked careers */}
            <div className="bg-white border border-cloud rounded-2xl p-6 sm:p-8 space-y-6">
              <div>
                <h3 className={`text-lg font-bold text-midnight ${headingFontClass}`}>
                  {t.needsPlanTitle}
                </h3>
                <p className="text-sm text-midnight/80 mt-1">{t.needsPlanIntro}</p>
              </div>

              <div className="space-y-4">
                {costAndAcademicBlocked.map((c) => {
                  const isExpanded = expandedBlockedIds.has(c.id);
                  const isMoneyBlocked = c.blocked?.gates.includes('money');
                  const isAcadBlocked = c.blocked?.gates.includes('academic');

                  return (
                    <div
                      key={c.id}
                      className="border border-cloud rounded-xl p-4 bg-cloud/10 space-y-3 transition-colors"
                    >
                      <button
                        type="button"
                        onClick={() => {
                          const next = new Set(expandedBlockedIds);
                          if (next.has(c.id)) next.delete(c.id);
                          else next.add(c.id);
                          setExpandedBlockedIds(next);
                        }}
                        className="w-full flex items-center justify-between text-left font-semibold text-midnight hover:text-ocean cursor-pointer"
                      >
                        <span className="text-base">{c.name[storeLang] ?? c.name.en}</span>
                        <span className="text-xs text-ocean font-medium">
                          {isExpanded ? '▲' : '▼'}
                        </span>
                      </button>

                      {isExpanded && (
                        <div className="pt-2 border-t border-cloud/60 space-y-2 text-sm text-midnight/80">
                          {isMoneyBlocked && (
                            <p className="text-xs sm:text-sm text-midnight/90">
                              • {t.gateCostSentence}
                            </p>
                          )}
                          {isAcadBlocked && (
                            <p className="text-xs sm:text-sm text-midnight/90">
                              • {t.gateAcademicSentence}
                            </p>
                          )}

                          {c.blocked && c.blocked.remedies.length > 0 ? (
                            <div className="mt-3 space-y-1.5 bg-paper/60 p-3 rounded-lg border border-cloud/50">
                              <span className="block text-xs font-semibold text-ocean">
                                {t.remediesHeader}
                              </span>
                              {c.blocked.remedies.map((rem) => {
                                const remedyText = rem.text[storeLang] ?? rem.text.en;
                                const isEnglishFallback = storeLang === 'hi' && rem.text.hi === null;

                                return (
                                  <div key={rem.id} className="text-xs text-midnight/85 flex items-start gap-1.5">
                                    <span>→</span>
                                    <span>
                                      {remedyText}
                                      {isEnglishFallback && (
                                        <span className="ml-1.5 px-1.5 py-0.5 rounded bg-cloud text-[10px] text-midnight/70 border border-cloud">
                                          {t.englishOnlyNote}
                                        </span>
                                      )}
                                    </span>
                                  </div>
                                );
                              })}
                            </div>
                          ) : (
                            <p className="text-xs text-midnight/70 italic mt-2">
                              {t.neutralRemedyLine}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          /* Main Explorer Balanced Layout */
          <div className="space-y-8 my-4 sm:my-6">
            {/* Top Interactive Workbench (2 Columns Balanced) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start">
              {/* Left Column (Chart & Slider Control Deck) */}
              <div className="lg:col-span-7 space-y-5">
                {/* Domain Filter Bar & Zoom Controls */}
                <div className="bg-white border border-cloud/80 rounded-2xl p-3 sm:p-4 flex flex-wrap items-center justify-between gap-2.5">
                  <div className="flex flex-wrap items-center gap-1.5">
                    {/* All domains toggle */}
                    <button
                      type="button"
                      onClick={() => setActiveDomains(new Set())}
                      className={`px-2.5 py-1 rounded-full text-xs font-medium transition-all cursor-pointer ${
                        activeDomains.size === 0
                          ? 'bg-midnight text-white'
                          : 'bg-cloud/30 text-midnight/70 hover:bg-cloud/60'
                      }`}
                    >
                      {t.allDomainsFilter}
                    </button>

                    {availableDomains.map((dom) => {
                      const isSelected = activeDomains.has(dom);
                      const sampleCareer = data.careers.find((c) => c.domain === dom);
                      const label = sampleCareer ? dom.replace(/_/g, ' ') : dom;

                      return (
                        <button
                          key={dom}
                          type="button"
                          onClick={() => {
                            const next = new Set(activeDomains);
                            if (next.has(dom)) next.delete(dom);
                            else next.add(dom);
                            setActiveDomains(next);
                          }}
                          className={`px-2.5 py-1 rounded-full text-xs font-medium capitalize border transition-all cursor-pointer ${
                            isSelected
                              ? 'bg-ocean text-white border-ocean'
                              : 'bg-white text-midnight/80 border-cloud hover:border-ocean/40'
                          }`}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>

                  {/* V2 Zoom Toggle Chip */}
                  {isZoomPossible && (
                    <button
                      type="button"
                      onClick={() => setIsZoomed(!isZoomed)}
                      className="ml-auto px-2.5 py-1 rounded-lg text-xs font-medium bg-cloud/50 text-ocean hover:bg-cloud border border-cloud/80 transition-colors cursor-pointer shrink-0"
                    >
                      {isZoomed
                        ? `${t.zoomedChip.replace('{min}', fmt(plotMin)).replace('{max}', fmt(plotMax))} (${t.showFullRange})`
                        : t.showZoomedRange}
                    </button>
                  )}
                </div>

                {/* The SVG Chart Container */}
                <div
                  className="bg-white border border-cloud/80 rounded-2xl p-2 sm:p-4 relative overflow-visible"
                  role="group"
                  aria-label={t.chartAriaLabel}
                >
                  {/* Floating Tooltip (Item 8) */}
                  {hoveredPoint && (
                    <div
                      className="absolute pointer-events-none z-30 transition-all duration-100"
                      style={{
                        left: `${Math.max(12, Math.min(84, hoveredPoint.xPct))}%`,
                        top: `${Math.max(6, hoveredPoint.yPct)}%`,
                        transform: 'translate(-50%, -105%)',
                      }}
                    >
                      <div className="bg-midnight text-white rounded-xl p-3 border border-cloud/40 min-w-[210px] max-w-[280px] space-y-1.5 text-xs">
                        <div className="flex items-start justify-between gap-2 border-b border-white/15 pb-1.5">
                          <div>
                            <span className="font-bold text-sm leading-tight block">
                              {hoveredPoint.career.name[storeLang] ?? hoveredPoint.career.name.en}
                            </span>
                            <span className="text-[10px] text-sky capitalize block">
                              {hoveredPoint.career.domain.replace(/_/g, ' ')}
                            </span>
                          </div>
                          {hoveredPoint.career.blend && (
                            <span className="px-1.5 py-0.5 rounded bg-ocean text-white font-mono font-bold text-[10px] shrink-0">
                              #{hoveredPoint.career.blend[sliderIdx]?.rank}
                            </span>
                          )}
                        </div>

                        {/* Coincident list preview */}
                        {hoveredPoint.members.length > 1 && (
                          <div className="text-[10px] text-white/80 pb-1 border-b border-white/10">
                            <span className="font-semibold text-sky">
                              +{hoveredPoint.members.length - 1} more here:
                            </span>{' '}
                            {hoveredPoint.members
                              .slice(1, 4)
                              .map((m) => m.name[storeLang] ?? m.name.en)
                              .join(', ')}
                          </div>
                        )}

                        {/* Scores in Tooltip */}
                        <div className="space-y-1 pt-0.5 text-[11px]">
                          {hoveredPoint.career.fit !== null && (
                            <div className="flex justify-between items-center text-white/90">
                              <span>{t.scoreFit}:</span>
                              <span className="font-mono font-bold text-sky">
                                {fmt(hoveredPoint.career.fit)}%
                              </span>
                            </div>
                          )}
                          {hoveredPoint.career.viability !== null ? (
                            <div className="flex justify-between items-center text-white/90">
                              <span>{t.scoreViability}:</span>
                              <span className="font-mono font-bold text-emerald-300">
                                {fmt(hoveredPoint.career.viability)}%
                              </span>
                            </div>
                          ) : (
                            <div className="text-[10px] text-amber-300 font-medium">
                              • {t.needsPlanTitle}
                            </div>
                          )}
                          <div className="flex justify-between items-center text-white/70 text-[10px]">
                            <span>{t.familyConflictLabel}:</span>
                            <span className="font-mono font-semibold">
                              {fmt(hoveredPoint.career.conflict)}/100
                            </span>
                          </div>
                        </div>

                        {/* Badges in Tooltip */}
                        <div className="flex flex-wrap gap-1 pt-1 text-[9px]">
                          {data.frontier.includes(hoveredPoint.career.id) && (
                            <span className="px-1.5 py-0.5 rounded bg-ocean/40 text-sky border border-ocean/50">
                              {t.chipBestTradeOff}
                            </span>
                          )}
                          {hoveredPoint.career.in_compromise && (
                            <span className="px-1.5 py-0.5 rounded bg-sky/30 text-sky border border-sky/40">
                              {t.chipCompromiseZone}
                            </span>
                          )}
                          {hoveredPoint.career.data_gaps.length > 0 && (
                            <span className="px-1.5 py-0.5 rounded bg-white/10 text-white/70 border border-white/10">
                              {t.chipEstimatedFigures}
                            </span>
                          )}
                        </div>

                        {/* Downward pointer triangle */}
                        <div className="absolute left-1/2 -bottom-1.5 -translate-x-1/2 w-3 h-3 bg-midnight rotate-45 border-r border-b border-cloud/40" />
                      </div>
                    </div>
                  )}

                  <svg
                    viewBox="0 0 560 500"
                    className="w-full h-auto aspect-square max-h-[520px] select-none"
                  >
                    <defs>
                      {/* Clip path for scatter plot area */}
                      <clipPath id="chartPlotClip">
                        <rect
                          x={xPlotLeft}
                          y={yPlotTop}
                          width={xPlotRight - xPlotLeft}
                          height={yPlotBottom - yPlotTop}
                          rx="10"
                        />
                      </clipPath>
                    </defs>

                    {/* Gutter Column Background (V5) */}
                    <rect
                      x="10"
                      y={yPlotTop}
                      width={xGutterDivider - 10}
                      height={yPlotBottom - yPlotTop}
                      rx="8"
                      fill="#F3F7FA"
                    />

                    {/* Gutter dividing line */}
                    <line
                      x1={xGutterDivider}
                      y1={yPlotTop}
                      x2={xGutterDivider}
                      y2={yPlotBottom}
                      stroke="#D8E2EE"
                      strokeWidth="1.5"
                      strokeDasharray="4 2"
                    />

                    {/* Gutter Label */}
                    <text
                      x={xGutterCenter}
                      y={yPlotTop - 14}
                      textAnchor="middle"
                      className="text-[10px] font-bold fill-midnight/70"
                    >
                      {t.gutterTitle}
                    </text>
                    <text
                      x={xGutterCenter}
                      y={yPlotTop - 3}
                      textAnchor="middle"
                      className="text-[9px] font-medium fill-midnight/50"
                    >
                      ({blockedCareers.filter((c) => c.fit !== null).length})
                    </text>

                    {/* Plot Background inside Clip */}
                    <rect
                      x={xPlotLeft}
                      y={yPlotTop}
                      width={xPlotRight - xPlotLeft}
                      height={yPlotBottom - yPlotTop}
                      rx="10"
                      fill="#FAFCFE"
                      stroke="#E3EEF8"
                      strokeWidth="1"
                    />

                    {/* Top-Right Quadrant: Sweet Spot Highlight (Item 4) */}
                    <g clipPath="url(#chartPlotClip)">
                      <rect
                        x={toX(Math.max(plotMin, 50))}
                        y={toY(100)}
                        width={Math.max(0, toX(100) - toX(Math.max(plotMin, 50)))}
                        height={Math.max(0, toY(Math.max(plotMin, 50)) - toY(100))}
                        fill="#E3EEF8"
                        fillOpacity="0.4"
                      />

                      {/* Sweet Spot Corner Label */}
                      <g transform={`translate(${xPlotRight - 10}, ${yPlotTop + 16})`}>
                        <rect
                          x="-175"
                          y="-11"
                          width="175"
                          height="18"
                          rx="4"
                          fill="#FFFFFF"
                          fillOpacity="0.88"
                          stroke="#E3EEF8"
                          strokeWidth="0.8"
                        />
                        <text
                          x="-6"
                          y="2"
                          textAnchor="end"
                          className="text-[9.5px] font-semibold fill-ocean pointer-events-none"
                        >
                          {t.sweetSpotLabel}
                        </text>
                      </g>

                      {/* Compromise Zone Rectangle (Item 5 & V2) */}
                      {data.compromise && (
                        <g>
                          <rect
                            x={toX(data.compromise.min_viability)}
                            y={toY(100)}
                            width={Math.max(0, toX(100) - toX(data.compromise.min_viability))}
                            height={Math.max(0, toY(data.compromise.min_fit) - toY(100))}
                            fill="#E3EEF8"
                            fillOpacity="0.5"
                            stroke="#2D6FB8"
                            strokeWidth="1.5"
                            strokeDasharray="5 3"
                          />
                          <g transform={`translate(${xPlotRight - 12}, ${toY(100) + 38})`}>
                            <rect
                              x="-115"
                              y="-11"
                              width="115"
                              height="18"
                              rx="4"
                              fill="#FFFFFF"
                              fillOpacity="0.92"
                              stroke="#7DBEF0"
                              strokeWidth="0.8"
                            />
                            <text
                              x="-6"
                              y="2"
                              textAnchor="end"
                              className="text-[10px] font-bold fill-ocean pointer-events-none"
                            >
                              {t.compromiseZoneLabel}
                            </text>
                          </g>
                        </g>
                      )}

                      {/* Grid Lines */}
                      {tickValues.map((val) => {
                        const x = toX(val);
                        const y = toY(val);
                        return (
                          <g key={val}>
                            {/* Horizontal gridline */}
                            <line
                              x1={xPlotLeft}
                              y1={y}
                              x2={xPlotRight}
                              y2={y}
                              stroke="#EEF3F8"
                              strokeWidth="1"
                            />
                            {/* Vertical gridline */}
                            <line
                              x1={x}
                              y1={yPlotTop}
                              x2={x}
                              y2={yPlotBottom}
                              stroke="#EEF3F8"
                              strokeWidth="1"
                            />
                          </g>
                        );
                      })}

                      {/* Stepped Pareto Frontier Line (V4) */}
                      {frontierPathD && (
                        <g>
                          <path
                            d={frontierPathD}
                            fill="none"
                            stroke="#2D6FB8"
                            strokeWidth="2.5"
                            className="pointer-events-none"
                          />
                          {/* Anchor nodes along frontier */}
                          {data.frontier.map((fId) => {
                            const c = nonBlockedCareers.find((car) => car.id === fId);
                            if (!c || c.viability === null || c.fit === null) return null;
                            return (
                              <circle
                                key={fId}
                                cx={toX(c.viability)}
                                cy={toY(c.fit)}
                                r="3.5"
                                fill="#2D6FB8"
                                stroke="#FFFFFF"
                                strokeWidth="1"
                                className="pointer-events-none"
                              />
                            );
                          })}
                        </g>
                      )}
                    </g>

                    {/* Stepped Frontier Label Badge */}
                    {frontierPathD && data.frontier.length >= 2 && (() => {
                      const firstCar = nonBlockedCareers.find((c) => c.id === data.frontier[0]);
                      if (!firstCar || firstCar.viability === null || firstCar.fit === null) return null;
                      const lx = toX(firstCar.viability);
                      const ly = Math.max(yPlotTop + 24, toY(firstCar.fit) - 14);
                      return (
                        <g transform={`translate(${lx}, ${ly})`} pointerEvents="none">
                          <rect
                            x="-4"
                            y="-11"
                            width="94"
                            height="18"
                            rx="4"
                            fill="#FFFFFF"
                            fillOpacity="0.9"
                            stroke="#2D6FB8"
                            strokeWidth="0.8"
                          />
                          <text
                            x="43"
                            y="2"
                            textAnchor="middle"
                            className="text-[9.5px] font-bold fill-ocean"
                          >
                            {t.bestTradeOffsLabel}
                          </text>
                        </g>
                      );
                    })()}

                    {/* Single Frontier Marker Ring (V4) */}
                    {data.frontier.length === 1 && (() => {
                      const single = nonBlockedCareers.find((c) => c.id === data.frontier[0]);
                      if (!single || single.viability === null || single.fit === null) return null;
                      const cx = toX(single.viability);
                      const cy = toY(single.fit);
                      return (
                        <g pointerEvents="none">
                          <circle
                            cx={cx}
                            cy={cy}
                            r="15"
                            fill="none"
                            stroke="#2D6FB8"
                            strokeWidth="2"
                            strokeDasharray="4 2"
                          />
                          <g transform={`translate(${cx}, ${cy - 20})`}>
                            <rect
                              x="-42"
                              y="-10"
                              width="84"
                              height="17"
                              rx="4"
                              fill="#FFFFFF"
                              fillOpacity="0.9"
                              stroke="#2D6FB8"
                              strokeWidth="0.8"
                            />
                            <text
                              x="0"
                              y="2"
                              textAnchor="middle"
                              className="text-[9.5px] font-bold fill-ocean"
                            >
                              {t.bestOnBothLabel}
                            </text>
                          </g>
                        </g>
                      );
                    })()}

                    {/* Tick Labels on Outer Border */}
                    {tickValues.map((val) => {
                      const x = toX(val);
                      const y = toY(val);
                      return (
                        <g key={val}>
                          <text
                            x={xPlotLeft - 6}
                            y={y + 4}
                            textAnchor="end"
                            className="text-[10px] font-medium fill-midnight/60 font-mono"
                          >
                            {val}
                          </text>
                          <text
                            x={x}
                            y={yPlotBottom + 16}
                            textAnchor="middle"
                            className="text-[10px] font-medium fill-midnight/60 font-mono"
                          >
                            {val}
                          </text>
                        </g>
                      );
                    })}

                    {/* Blocked Careers in Gutter (V5) */}
                    {gutterBlockedGroups.map((grp) => {
                      const cy = toY(grp.fit);
                      const isSelected = grp.members.some((m) => m.id === selectedCareerId);
                      const isNoRoute = grp.cause === 'no_route_data';

                      return (
                        <g
                          key={grp.key}
                          className="cursor-pointer"
                          onClick={() => {
                            lastFocusedTriggerRef.current = document.activeElement as HTMLElement;
                            if (grp.count > 1) {
                              setSelectedGroupMembers(grp.members);
                            } else {
                              setSelectedGroupMembers(null);
                            }
                            setSelectedCareerId(grp.representative.id);
                          }}
                          onMouseEnter={() => {
                            setHoveredCareerId(grp.representative.id);
                            setHoveredPoint({
                              career: grp.representative,
                              members: grp.members,
                              xPct: (xGutterCenter / 560) * 100,
                              yPct: (cy / 500) * 100,
                            });
                          }}
                          onMouseLeave={() => {
                            setHoveredCareerId(null);
                            setHoveredPoint(null);
                          }}
                        >
                          {isSelected && (
                            <circle
                              cx={xGutterCenter}
                              cy={cy}
                              r="10"
                              fill="none"
                              stroke="#11284A"
                              strokeWidth="2"
                            />
                          )}
                          <circle
                            cx={xGutterCenter}
                            cy={cy}
                            r="6"
                            fill="transparent"
                            stroke="#7DBEF0"
                            strokeWidth="1.8"
                            strokeDasharray={isNoRoute ? '1.5 2' : '3 2'}
                            opacity={isNoRoute ? 0.4 : 1.0}
                          />
                          {grp.count > 1 && (
                            <text
                              x={xGutterCenter + 9}
                              y={cy + 3}
                              className="text-[9px] font-bold fill-midnight/70 font-mono"
                            >
                              +{grp.count}
                            </text>
                          )}
                        </g>
                      );
                    })}

                    {/* Coincident Non-Blocked Career Dots (Item 7 & V3) */}
                    {coincidentGroups.map((grp) => {
                      const cx = toX(grp.viability);
                      const cy = toY(grp.fit);
                      const rep = grp.representative;
                      const rank = grp.rank;

                      const isDimmed =
                        activeDomains.size > 0 && !activeDomains.has(rep.domain);
                      const isSelected = grp.members.some((m) => m.id === selectedCareerId);
                      const isHovered = grp.members.some((m) => m.id === hoveredCareerId);
                      const isEstimated = rep.data_gaps.length > 0;

                      // Rank-based styling
                      let radius = 4;
                      let fill = '#2D6FB8';
                      let opacity = isDimmed ? 0.25 : 1.0;
                      let hasLabel = false;

                      if (rank === 1) {
                        radius = 9.5;
                        fill = '#11284A'; // midnight
                        hasLabel = true;
                      } else if (rank <= 3) {
                        radius = 7.5;
                        fill = '#2D6FB8'; // ocean
                        hasLabel = true;
                      } else if (rank <= 10) {
                        radius = 5.5;
                        fill = '#2D6FB8';
                      } else {
                        radius = 4;
                        opacity = isDimmed ? 0.2 : 0.55;
                      }

                      if (isEstimated) {
                        fill = '#E3EEF8'; // cloud fill with ocean stroke
                      }

                      if (isSelected || isHovered) {
                        hasLabel = true;
                      }

                      // Label placement flipped on right side
                      const flipLabelLeft = cx > xPlotLeft + (xPlotRight - xPlotLeft) * 0.74;
                      const labelX = flipLabelLeft ? cx - radius - 7 : cx + radius + 7;
                      const textAnchor = flipLabelLeft ? 'end' : 'start';

                      return (
                        <g
                          key={grp.key}
                          className="cursor-pointer transition-transform"
                          onClick={() => {
                            lastFocusedTriggerRef.current = document.activeElement as HTMLElement;
                            if (grp.count > 1) {
                              setSelectedGroupMembers(grp.members);
                            } else {
                              setSelectedGroupMembers(null);
                            }
                            setSelectedCareerId(rep.id);
                          }}
                          onMouseEnter={() => {
                            setHoveredCareerId(rep.id);
                            setHoveredPoint({
                              career: rep,
                              members: grp.members,
                              xPct: (cx / 560) * 100,
                              yPct: (cy / 500) * 100,
                            });
                          }}
                          onMouseLeave={() => {
                            setHoveredCareerId(null);
                            setHoveredPoint(null);
                          }}
                        >
                          {/* Extra ring when selected */}
                          {isSelected && (
                            <circle
                              cx={cx}
                              cy={cy}
                              r={radius + 4.5}
                              fill="none"
                              stroke="#11284A"
                              strokeWidth="2"
                            />
                          )}

                          {/* Dot marker */}
                          <circle
                            cx={cx}
                            cy={cy}
                            r={radius}
                            fill={fill}
                            stroke={isEstimated ? '#2D6FB8' : '#FFFFFF'}
                            strokeWidth={isEstimated ? 2 : 1.5}
                            opacity={opacity}
                          />

                          {/* Coincident Count Badge (V3) */}
                          {grp.count > 1 && (
                            <g pointerEvents="none">
                              <circle
                                cx={cx + radius}
                                cy={cy - radius}
                                r="6"
                                fill="#11284A"
                                stroke="#FFFFFF"
                                strokeWidth="1"
                              />
                              <text
                                x={cx + radius}
                                y={cy - radius + 3}
                                textAnchor="middle"
                                className="text-[8px] font-bold fill-white font-mono"
                              >
                                {grp.count}
                              </text>
                            </g>
                          )}

                          {/* Pill Backdrop & Label for Rank 1-3, selected, or hovered */}
                          {hasLabel && (
                            <g pointerEvents="none">
                              <text
                                x={labelX}
                                y={cy + 3.5}
                                textAnchor={textAnchor}
                                className={`text-[11px] font-semibold fill-midnight ${
                                  rank === 1 ? 'font-bold' : ''
                                }`}
                                style={{
                                  paintOrder: 'stroke',
                                  stroke: '#FFFFFF',
                                  strokeWidth: 3.5,
                                  strokeLinejoin: 'round',
                                }}
                              >
                                {grp.count > 1 && isHovered
                                  ? `${grp.members
                                      .slice(0, 3)
                                      .map((m) => m.name[storeLang] ?? m.name.en)
                                      .join(', ')}${
                                      grp.count > 3 ? ` +${grp.count - 3}` : ''
                                    }`
                                  : `${rep.name[storeLang] ?? rep.name.en}${
                                      isEstimated ? '*' : ''
                                    }`}
                              </text>
                            </g>
                          )}
                        </g>
                      );
                    })}

                    {/* Axes Title Labels */}
                    <text
                      x={(xPlotLeft + xPlotRight) / 2}
                      y={yPlotBottom + 36}
                      textAnchor="middle"
                      className="text-xs font-semibold fill-midnight"
                    >
                      {t.xAxisLabel} →
                    </text>

                    <text
                      x={xPlotLeft + 8}
                      y={yPlotTop - 12}
                      textAnchor="start"
                      className="text-xs font-semibold fill-midnight"
                    >
                      ↑ {t.yAxisLabel.replace('{student}', studentName)}
                    </text>
                  </svg>

                  {/* Chart Legend & Coverage Summary (V8) */}
                  <div className="mt-3 pt-3 border-t border-cloud/60 text-xs text-midnight/80 space-y-2">
                    <div className="flex flex-wrap items-center gap-3 sm:gap-4 text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <span className="w-3.5 h-3.5 rounded-full bg-midnight inline-block" />
                        <span className="font-medium">{t.legendTopPick}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-3.5 h-3.5 rounded-full bg-ocean inline-block" />
                        <span className="font-medium">{t.legendFrontier}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-3.5 h-3.5 rounded-full bg-cloud border-2 border-ocean inline-block" />
                        <span className="font-medium">{t.legendEstimated}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-3.5 h-3.5 rounded-full border-2 border-dashed border-sky inline-block" />
                        <span className="font-medium">{t.legendNeedsPlan}</span>
                      </div>
                    </div>
                    <p className="text-[11px] text-midnight/60 leading-relaxed">
                      {t.legendCoverageNote
                        .replace('{n}', verifiedCareersCount.toString())
                        .replace('{total}', data.careers.length.toString())}
                    </p>
                  </div>
                </div>

                {/* The Slider Control Deck (Redesigned Heart of the Page) */}
                <div className="bg-white border border-cloud/80 rounded-2xl p-4 sm:p-6 space-y-4">
                  {/* Dynamic Balance Header */}
                  <div className="flex items-center justify-between text-xs font-bold text-midnight">
                    <div className="flex items-center gap-1.5">
                      <span>
                        {t.sliderBalanceStudent.replace('{student}', studentName)}:
                      </span>
                      <span className="font-mono text-ocean text-xs">
                        {100 - sliderPos}%
                      </span>
                    </div>

                    <div className="px-2.5 py-0.5 rounded-full bg-cloud/50 border border-cloud text-[11px] font-semibold text-midnight">
                      {t.sliderBalancePill
                        .replace('{studentPct}', (100 - sliderPos).toString())
                        .replace('{familyPct}', sliderPos.toString())}
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span>{t.sliderBalanceFamily}:</span>
                      <span className="font-mono text-midnight text-xs">
                        {sliderPos}%
                      </span>
                    </div>
                  </div>

                  {/* Range Slider Track with Visual Snap Ticks */}
                  <div className="relative pt-2 pb-1">
                    <input
                      type="range"
                      min="0"
                      max="100"
                      step="5"
                      value={sliderPos}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10);
                        if (data.slider.positions.includes(val)) {
                          setSliderPos(val);
                        } else {
                          const closest = data.slider.positions.reduce((prev, curr) =>
                            Math.abs(curr - val) < Math.abs(prev - val) ? curr : prev
                          );
                          setSliderPos(closest);
                        }
                      }}
                      aria-valuetext={t.sliderAriaValue.replace('{val}', sliderPos.toString())}
                      className="w-full h-3 rounded-lg appearance-none cursor-pointer accent-ocean focus-visible:outline-2 focus-visible:outline-ocean"
                      style={{
                        background: '#E3EEF8',
                      }}
                    />

                    {/* Snap Tick Indicators */}
                    <div className="flex justify-between text-[10px] text-midnight/50 font-mono pt-1">
                      <span>0% (Student)</span>
                      <span>25%</span>
                      <span>50% (Equal)</span>
                      <span>75%</span>
                      <span>100% (Family)</span>
                    </div>
                  </div>

                  {/* Winner Strip (Item 10) */}
                  <div className="space-y-1.5 pt-1">
                    <div className="relative w-full h-7 bg-cloud/40 rounded-lg overflow-hidden flex border border-cloud/70">
                      {winnerStripSegments.map((seg, idx) => {
                        const isCurrent =
                          sliderPos >= seg.startPos && sliderPos <= seg.endPos;
                        const isComp = seg.career.in_compromise;
                        const hasGaps = seg.career.data_gaps.length > 0;
                        const careerName = seg.career.name[storeLang] ?? seg.career.name.en;
                        const widthPct = (seg.length / data.slider.positions.length) * 100;

                        return (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => setSliderPos(seg.startPos)}
                            title={`${careerName} (${seg.startPos}–${seg.endPos})`}
                            className={`h-full border-r border-white/70 text-[10px] font-medium flex items-center justify-center truncate px-1 transition-colors cursor-pointer ${
                              isComp ? 'bg-sky/60 hover:bg-sky/80' : 'bg-cloud/70 hover:bg-cloud'
                            } ${isCurrent ? 'ring-2 ring-inset ring-midnight font-bold' : ''}`}
                            style={{ width: `${widthPct}%` }}
                          >
                            {widthPct >= 14 && (
                              <span className="truncate">
                                {careerName}
                                {hasGaps ? '*' : ''}
                              </span>
                            )}
                          </button>
                        );
                      })}

                      {/* Active slider indicator line */}
                      <div
                        className="absolute top-0 bottom-0 w-1 bg-midnight pointer-events-none transition-all duration-75"
                        style={{ left: `${sliderPos}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-midnight/60">
                      <span>{t.winnerStripCaption}</span>
                      {winnerStripSegments.some((s) => s.career.data_gaps.length > 0) && (
                        <span>{t.winnerStripEstimatedAsterisk}</span>
                      )}
                    </div>
                  </div>

                  {/* Top Pick Hero Showcase Banner */}
                  {currentWinner && (
                    <div className="p-3.5 bg-paper rounded-xl border border-cloud/80 space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5">
                          <span className="px-2 py-0.5 rounded-full bg-midnight text-white text-[10px] font-bold">
                            {t.heroTopMatch}
                          </span>
                          <span className="text-xs font-semibold text-ocean capitalize">
                            {currentWinner.domain.replace(/_/g, ' ')}
                          </span>
                        </div>
                        {currentWinner.in_compromise && (
                          <span className="px-2 py-0.5 rounded-full bg-sky/30 text-midnight text-[10px] font-semibold">
                            {t.chipCompromiseZone}
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <h4 className="text-base font-bold text-midnight">
                          {currentWinner.name[storeLang] ?? currentWinner.name.en}
                        </h4>
                        <div className="flex items-center gap-3 text-xs font-mono">
                          <span className="text-ocean font-semibold">
                            {t.scoreFit}: {fmt(currentWinner.fit)}%
                          </span>
                          {currentWinner.viability !== null && (
                            <span className="text-midnight font-semibold">
                              {t.scoreViability}: {fmt(currentWinner.viability)}%
                            </span>
                          )}
                        </div>
                      </div>

                      <p className="text-xs text-midnight/80 leading-relaxed">
                        {currentWinner.viability !== null
                          ? t.sliderTopPickSentence
                              .replace(
                                '{career}',
                                currentWinner.name[storeLang] ?? currentWinner.name.en
                              )
                              .replace('{fit}', fmt(currentWinner.fit))
                              .replace('{viability}', fmt(currentWinner.viability))
                          : t.sliderTopPickSentenceNoViab
                              .replace(
                                '{career}',
                                currentWinner.name[storeLang] ?? currentWinner.name.en
                              )
                              .replace('{fit}', fmt(currentWinner.fit))}
                      </p>

                      {currentWinner.data_gaps.length > 0 && (
                        <p className="text-[11px] text-ocean/80 italic">
                          • {t.sliderTopPickEstimated}
                        </p>
                      )}

                      <div className="pt-1 border-t border-cloud/60 text-[11px] text-midnight/60">
                        {t.sliderDisagreementNote}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column (Selected Career Inspector & Ranked Priority List) */}
              <div className="lg:col-span-5 space-y-5">
                {/* Selected Career Deep-Dive Panel */}
                <AnimatePresence mode="wait">
                  {selectedCareer && (
                    <motion.div
                      ref={detailPanelRef}
                      key={selectedCareer.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      transition={{ duration: 0.15 }}
                      className="bg-white border border-ocean/30 rounded-2xl p-4 sm:p-5 space-y-3.5"
                    >
                      <div className="flex items-start justify-between gap-2 border-b border-cloud/60 pb-2.5">
                        <div>
                          <span className="text-[10px] font-bold text-ocean uppercase tracking-wider block">
                            {t.detailPanelTitle}
                          </span>
                          <h4 className={`text-lg font-bold text-midnight ${headingFontClass}`}>
                            {selectedCareer.name[storeLang] ?? selectedCareer.name.en}
                          </h4>
                          <span className="text-xs text-midnight/60 capitalize">
                            {selectedCareer.domain.replace(/_/g, ' ')}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedCareerId(null);
                            setSelectedGroupMembers(null);
                            lastFocusedTriggerRef.current?.focus();
                          }}
                          className="text-midnight/50 hover:text-midnight text-base font-bold p-1 rounded-md cursor-pointer"
                          aria-label={t.closeDetail}
                        >
                          ✕
                        </button>
                      </div>

                      {/* Coincident Group Switcher (V3) */}
                      {selectedGroupMembers && selectedGroupMembers.length > 1 && (
                        <div className="p-2.5 bg-cloud/30 rounded-xl border border-cloud space-y-1.5">
                          <span className="text-xs font-semibold text-midnight">
                            {t.coincidentGroupTitle.replace(
                              '{count}',
                              selectedGroupMembers.length.toString()
                            )}
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {selectedGroupMembers.map((m) => (
                              <button
                                key={m.id}
                                type="button"
                                onClick={() => setSelectedCareerId(m.id)}
                                className={`px-2 py-0.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                                  m.id === selectedCareer.id
                                    ? 'bg-midnight text-white'
                                    : 'bg-white border border-cloud text-midnight hover:border-ocean'
                                }`}
                              >
                                {m.name[storeLang] ?? m.name.en}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Rank & Blend score banner */}
                      {selectedCareer.blend && (
                        <div className="flex justify-between items-center text-xs font-semibold p-2 bg-paper rounded-xl border border-cloud">
                          <span className="text-midnight">
                            {t.rankAtPosition.replace(
                              '{rank}',
                              selectedCareer.blend[sliderIdx].rank.toString()
                            )}
                          </span>
                          <span className="text-ocean font-mono text-sm font-bold">
                            {fmt(selectedCareer.blend[sliderIdx].score)} / 100
                          </span>
                        </div>
                      )}

                      {/* Component score bars */}
                      <div className="space-y-2 text-xs">
                        {selectedCareer.fit !== null && (
                          <div className="space-y-1">
                            <div className="flex justify-between text-midnight/80">
                              <span>{t.scoreFit}</span>
                              <span className="font-mono font-bold text-ocean">
                                {fmt(selectedCareer.fit)}%
                              </span>
                            </div>
                            <div className="w-full h-2 bg-cloud rounded-full overflow-hidden">
                              <div
                                className="h-full bg-ocean rounded-full transition-all duration-300"
                                style={{ width: `${selectedCareer.fit}%` }}
                              />
                            </div>
                          </div>
                        )}

                        {selectedCareer.viability !== null && (
                          <div className="space-y-1">
                            <div className="flex justify-between text-midnight/80">
                              <span>{t.scoreViability}</span>
                              <span className="font-mono font-bold text-midnight">
                                {fmt(selectedCareer.viability)}%
                              </span>
                            </div>
                            <div className="w-full h-2 bg-cloud rounded-full overflow-hidden">
                              <div
                                className="h-full bg-midnight rounded-full transition-all duration-300"
                                style={{ width: `${selectedCareer.viability}%` }}
                              />
                            </div>
                          </div>
                        )}

                        {/* V7: Market bar ONLY when market is non-null */}
                        {selectedCareer.market !== null && (
                          <div className="space-y-1">
                            <div className="flex justify-between text-midnight/80">
                              <span>{t.scoreMarket}</span>
                              <span className="font-mono font-bold text-sky">
                                {fmt(selectedCareer.market)}%
                              </span>
                            </div>
                            <div className="w-full h-2 bg-cloud rounded-full overflow-hidden">
                              <div
                                className="h-full bg-sky rounded-full"
                                style={{ width: `${selectedCareer.market}%` }}
                              />
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Metric info rows */}
                      <div className="pt-2 border-t border-cloud/60 space-y-1.5 text-xs text-midnight/80">
                        <div className="flex items-center justify-between">
                          <span>{t.familyConflictLabel}:</span>
                          <span className="font-mono font-bold text-midnight">
                            {t.conflictScore.replace('{score}', fmt(selectedCareer.conflict))}
                          </span>
                        </div>

                        {selectedCareer.years_to_income !== null && (
                          <div className="flex items-center justify-between">
                            <span>{t.yearsToIncome}:</span>
                            <span className="font-semibold text-midnight">
                              {t.yearsCount.replace(
                                '{n}',
                                selectedCareer.years_to_income.toString()
                              )}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Data gaps note when non-empty */}
                      {selectedCareer.data_gaps.length > 0 && (
                        <div className="pt-2 border-t border-cloud/60 space-y-1 text-xs text-midnight/70">
                          <span className="font-semibold text-ocean">
                            {t.estimatedNoteTitle}:
                          </span>
                          <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                            {selectedCareer.data_gaps.map((gap) => (
                              <li key={gap}>{getDataGapLabel(gap)}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div className="text-[10px] text-midnight/40 text-right">
                        PRISM Snapshot v0.1
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Ranked Careers Priority List (Item 11) */}
                <div className="bg-white border border-cloud/80 rounded-2xl p-4 sm:p-5 space-y-3">
                  <div className="flex items-center justify-between border-b border-cloud/60 pb-2.5">
                    <div>
                      <h3 className={`text-base font-bold text-midnight ${headingFontClass}`}>
                        {t.rankedListTitle}
                      </h3>
                      <span className="text-[11px] text-midnight/60">
                        {t.clickToInspectHint}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowAllNonBlocked(!showAllNonBlocked)}
                      className="text-xs font-semibold text-ocean hover:underline cursor-pointer"
                    >
                      {showAllNonBlocked
                        ? t.showTop10Toggle
                        : t.showAllToggle.replace('{count}', rankedNonBlocked.length.toString())}
                    </button>
                  </div>

                  {/* Scrollable List Container (Aligns height with Left Column) */}
                  <div className="max-h-[500px] overflow-y-auto pr-1 space-y-2">
                    {(showAllNonBlocked ? rankedNonBlocked : rankedNonBlocked.slice(0, 10)).map(
                      (c) => {
                        const rank = c.blend![sliderIdx].rank;
                        const score = c.blend![sliderIdx].score;
                        const isSelected = c.id === selectedCareerId;
                        const isFrontier = data.frontier.includes(c.id);
                        const isComp = c.in_compromise;
                        const hasGaps = c.data_gaps.length > 0;

                        return (
                          <motion.div
                            key={c.id}
                            layout={!shouldReduceMotion}
                            onClick={() => {
                              lastFocusedTriggerRef.current = document.activeElement as HTMLElement;
                              setSelectedCareerId(c.id);
                              setSelectedGroupMembers(null);
                            }}
                            tabIndex={0}
                            role="button"
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault();
                                setSelectedCareerId(c.id);
                                setSelectedGroupMembers(null);
                              }
                            }}
                            className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer focus-visible:outline-2 focus-visible:outline-ocean ${
                              isSelected
                                ? 'bg-cloud/50 border-midnight/70 ring-1 ring-midnight/30'
                                : 'bg-paper/40 border-cloud hover:border-ocean/40'
                            }`}
                          >
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-2 min-w-0">
                                <span
                                  className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold shrink-0 ${
                                    rank === 1
                                      ? 'bg-midnight text-white'
                                      : rank <= 3
                                      ? 'bg-ocean text-white'
                                      : 'bg-cloud text-midnight'
                                  }`}
                                >
                                  #{rank}
                                </span>
                                <span className="font-semibold text-xs sm:text-sm text-midnight truncate">
                                  {c.name[storeLang] ?? c.name.en}
                                </span>
                              </div>
                              <span className="text-xs font-bold font-mono text-ocean shrink-0">
                                {fmt(score)}
                              </span>
                            </div>

                            {/* Fit & Affordability Thin Bars */}
                            <div className="grid grid-cols-2 gap-2 mt-1.5 pt-1.5 border-t border-cloud/40 text-[10px] text-midnight/70">
                              <div>
                                <div className="flex justify-between mb-0.5">
                                  <span>{t.scoreFit}</span>
                                  <span className="font-mono font-medium">{fmt(c.fit)}</span>
                                </div>
                                <div className="w-full h-1 bg-cloud rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-ocean rounded-full"
                                    style={{ width: `${c.fit ?? 0}%` }}
                                  />
                                </div>
                              </div>
                              <div>
                                <div className="flex justify-between mb-0.5">
                                  <span>{t.scoreViability}</span>
                                  <span className="font-mono font-medium">
                                    {fmt(c.viability)}
                                  </span>
                                </div>
                                <div className="w-full h-1 bg-cloud rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-midnight rounded-full"
                                    style={{ width: `${c.viability ?? 0}%` }}
                                  />
                                </div>
                              </div>
                            </div>

                            {/* Chips */}
                            <div className="flex flex-wrap gap-1 mt-1.5">
                              {isFrontier && (
                                <span className="px-1.5 py-0.5 bg-ocean/10 text-ocean rounded text-[9.5px] font-semibold">
                                  {t.chipBestTradeOff}
                                </span>
                              )}
                              {isComp && (
                                <span className="px-1.5 py-0.5 bg-sky/30 text-midnight rounded text-[9.5px] font-semibold">
                                  {t.chipCompromiseZone}
                                </span>
                              )}
                              {hasGaps && (
                                <span className="px-1.5 py-0.5 bg-cloud text-midnight/70 rounded text-[9.5px] font-medium border border-cloud">
                                  {t.chipEstimatedFigures}
                                </span>
                              )}
                            </div>
                          </motion.div>
                        );
                      }
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Bottom Balanced Section: Action Plans & Pathways (Blocked Careers) */}
            {blockedCareers.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start mt-8">
                {/* Left Card: Needs a Plan (Cost & Academic Gates) */}
                <div className="bg-white border border-cloud/80 rounded-2xl p-4 sm:p-6 space-y-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className={`text-base font-bold text-midnight ${headingFontClass}`}>
                        {t.needsPlanTitle} ({costAndAcademicBlocked.length})
                      </h4>
                    </div>
                    <p className="text-xs text-midnight/70 mt-1">
                      {t.needsPlanIntro}
                    </p>
                  </div>

                  <div className="space-y-3">
                    {costAndAcademicBlocked.map((c) => {
                      const isExpanded = expandedBlockedIds.has(c.id);
                      const isMoneyBlocked = c.blocked?.gates.includes('money');
                      const isAcadBlocked = c.blocked?.gates.includes('academic');

                      return (
                        <div
                          key={c.id}
                          className="border border-cloud rounded-xl p-3 bg-cloud/10 space-y-2 transition-colors"
                        >
                          <button
                            type="button"
                            onClick={() => {
                              const next = new Set(expandedBlockedIds);
                              if (next.has(c.id)) next.delete(c.id);
                              else next.add(c.id);
                              setExpandedBlockedIds(next);
                            }}
                            className="w-full flex items-center justify-between text-left font-semibold text-xs sm:text-sm text-midnight hover:text-ocean cursor-pointer"
                          >
                            <span>{c.name[storeLang] ?? c.name.en}</span>
                            <span className="text-xs text-ocean font-medium">
                              {isExpanded ? '▲' : '▼'}
                            </span>
                          </button>

                          {isExpanded && (
                            <div className="pt-2 border-t border-cloud/60 space-y-2 text-xs text-midnight/80">
                              {isMoneyBlocked && (
                                <p className="text-[11px] text-midnight/90">
                                  • {t.gateCostSentence}
                                </p>
                              )}
                              {isAcadBlocked && (
                                <p className="text-[11px] text-midnight/90">
                                  • {t.gateAcademicSentence}
                                </p>
                              )}

                              {c.blocked && c.blocked.remedies.length > 0 ? (
                                <div className="mt-2 space-y-1.5 bg-paper/60 p-2.5 rounded-lg border border-cloud/50">
                                  <span className="block font-semibold text-ocean text-[11px]">
                                    {t.remediesHeader}
                                  </span>
                                  {c.blocked.remedies.map((rem) => {
                                    const remedyText =
                                      rem.text[storeLang] ?? rem.text.en;
                                    const isEnglishFallback =
                                      storeLang === 'hi' && rem.text.hi === null;

                                    return (
                                      <div
                                        key={rem.id}
                                        className="text-[11px] text-midnight/85 flex items-start gap-1"
                                      >
                                        <span>→</span>
                                        <span>
                                          {remedyText}
                                          {isEnglishFallback && (
                                            <span className="ml-1 px-1 py-0.5 rounded bg-cloud text-[9px] text-midnight/70 border border-cloud">
                                              {t.englishOnlyNote}
                                            </span>
                                          )}
                                        </span>
                                      </div>
                                    );
                                  })}
                                </div>
                              ) : (
                                <p className="text-[11px] text-midnight/60 italic mt-1">
                                  {t.neutralRemedyLine}
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Right Card: Not Enough Data Yet (no_route_data) */}
                <div className="bg-white border border-cloud/80 rounded-2xl p-4 sm:p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <h4 className={`text-base font-bold text-midnight/90 ${headingFontClass}`}>
                        {t.notEnoughDataTitle} ({noRouteDataBlocked.length})
                      </h4>
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        setShowNoRouteDataSection(!showNoRouteDataSection)
                      }
                      className="text-xs text-ocean font-medium cursor-pointer"
                    >
                      {showNoRouteDataSection ? '▲' : '▼'}
                    </button>
                  </div>

                  <p className="text-xs text-midnight/70 leading-relaxed">
                    {t.notEnoughDataIntro}
                  </p>

                  <div className="space-y-2 pt-1">
                    <div className="flex flex-wrap gap-1.5">
                      {noRouteDataBlocked.map((c) => (
                        <span
                          key={c.id}
                          className="px-2.5 py-1 rounded-lg bg-paper border border-cloud text-xs font-medium text-midnight/80"
                        >
                          {c.name[storeLang] ?? c.name.en}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Screening Footer Note (Rule 12) */}
        <footer className="mt-12 pt-6 border-t border-cloud/60 text-center">
          <p className="text-xs text-midnight/60 leading-relaxed max-w-lg mx-auto">
            {t.explorerFooterNote}
          </p>
        </footer>
      </div>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

import { logger } from "@/lib/observability/logger";
import { recordTiming } from "@/lib/observability/timingStore";

export { getRecentTimings } from "@/lib/observability/timingStore";
export type { TimingRecord } from "@/lib/observability/timingStore";

/** Measure a named operation (e.g. analysis execution). */
export function usePerformanceTiming(label: string) {
  const startRef = useRef<number | null>(null);
  const [lastDurationMs, setLastDurationMs] = useState<number | null>(null);

  const start = useCallback(() => {
    startRef.current = performance.now();
    logger.debug(`Timing started: ${label}`);
  }, [label]);

  const end = useCallback(() => {
    if (startRef.current == null) return null;
    const durationMs = performance.now() - startRef.current;
    startRef.current = null;
    setLastDurationMs(durationMs);
    const entry = recordTiming(label, durationMs);
    logger.debug(`Timing: ${label}`, { durationMs: Math.round(durationMs) });
    return entry;
  }, [label]);

  const reset = useCallback(() => {
    startRef.current = null;
    setLastDurationMs(null);
  }, []);

  return { start, end, reset, lastDurationMs };
}

/** Track route transition duration on pathname change. */
export function useRouteTransitionTiming() {
  const pathname = usePathname();
  const previousPath = useRef<string | null>(null);
  const routeStart = useRef<number>(performance.now());
  const [lastRouteMs, setLastRouteMs] = useState<number | null>(null);

  useEffect(() => {
    const now = performance.now();
    if (previousPath.current && previousPath.current !== pathname) {
      const durationMs = now - routeStart.current;
      setLastRouteMs(durationMs);
      recordTiming(`route:${previousPath.current}→${pathname}`, durationMs);
    }
    previousPath.current = pathname;
    routeStart.current = now;
  }, [pathname]);

  return { pathname, lastRouteMs };
}

/**
 * Placeholder hook for component render timing.
 * Full Profiler integration deferred — exposes manual mark API.
 */
export function useRenderTiming(componentName: string) {
  const mountTime = useRef(performance.now());

  useEffect(() => {
    const durationMs = performance.now() - mountTime.current;
    recordTiming(`render:${componentName}`, durationMs);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount only
  }, []);

  const mark = useCallback(
    (phase: string) => {
      recordTiming(`render:${componentName}:${phase}`, performance.now() - mountTime.current);
    },
    [componentName],
  );

  return { mark };
}

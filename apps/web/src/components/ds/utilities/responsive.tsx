"use client";

import { useEffect, useState, type ReactNode } from "react";

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia(query);
    const onChange = () => setMatches(mq.matches);
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}

export const breakpoints = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
} as const;

export type Breakpoint = keyof typeof breakpoints;

export type HideBelowProps = {
  breakpoint: Breakpoint;
  children: ReactNode;
};

/** Hide children when viewport is below the given breakpoint. */
export function HideBelow({ breakpoint, children }: HideBelowProps) {
  const matches = useMediaQuery(`(min-width: ${breakpoints[breakpoint]}px)`);
  if (!matches) return null;
  return <>{children}</>;
}

export type ShowAboveProps = {
  breakpoint: Breakpoint;
  children: ReactNode;
};

/** Show children only when viewport is at/above the given breakpoint. */
export function ShowAbove({ breakpoint, children }: ShowAboveProps) {
  const matches = useMediaQuery(`(min-width: ${breakpoints[breakpoint]}px)`);
  if (!matches) return null;
  return <>{children}</>;
}

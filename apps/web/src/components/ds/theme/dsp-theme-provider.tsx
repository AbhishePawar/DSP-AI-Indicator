"use client";

/**
 * Optional next-themes bridge (EPIC-F001).
 * Keeps `data-theme` in sync for PR1.2 CSS variables.
 * Existing app layout continues to use `@/providers/ThemeProvider`.
 */

import { ThemeProvider as NextThemesProvider, useTheme as useNextTheme } from "next-themes";
import {
  useEffect,
  type ReactNode,
} from "react";

function DataThemeSync({ children }: { children: ReactNode }) {
  const { resolvedTheme } = useNextTheme();
  useEffect(() => {
    if (!resolvedTheme) return;
    document.documentElement.dataset.theme =
      resolvedTheme === "dark" ? "dark" : "light";
  }, [resolvedTheme]);
  return children;
}

export function DspThemeProvider({ children }: { children: ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      storageKey="dsp.theme.next.v1"
      disableTransitionOnChange
    >
      <DataThemeSync>{children}</DataThemeSync>
    </NextThemesProvider>
  );
}

export { useNextTheme };

"use client";

/**
 * Figma Make AppLayout mobile top bar — hamburger + logo, shown below md.
 * Desktop uses the sidebar as the only application chrome.
 */

import Link from "next/link";

import { Button } from "@/components/ds";
import { useUiStore } from "@/lib/shell";

export function Topbar({
  onMenuClick,
}: {
  onMenuClick: () => void;
  /** Kept for call-site compatibility; the Figma shell has no desktop collapse control. */
  onToggleCollapse?: () => void;
  sidebarCollapsed?: boolean;
}) {
  const setCommandPaletteOpen = useUiStore((s) => s.setCommandPaletteOpen);

  return (
    <header
      aria-label="Application header"
      className="flex shrink-0 items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--surface)] px-4 py-2 md:hidden"
    >
      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          className="min-h-11 min-w-11 px-3"
          onClick={onMenuClick}
          aria-label="Open navigation menu"
        >
          <span aria-hidden>☰</span>
        </Button>
        <Link
          href="/dashboard"
          className="flex min-h-11 items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          <span className="dsp-logo-mark" aria-hidden />
          <span className="font-[family-name:var(--font-display)] text-base text-[var(--fg)]">
            DSP
          </span>
        </Link>
      </div>
      <Button
        variant="ghost"
        size="sm"
        className="min-h-11"
        onClick={() => setCommandPaletteOpen(true)}
        aria-label="Open command palette"
      >
        Commands
      </Button>
    </header>
  );
}

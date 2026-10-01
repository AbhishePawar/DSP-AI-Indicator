"use client";

/**
 * Figma Make AppLayout top bar — always visible, 48px, client identity on the right.
 * Search stays available but visually secondary. Mobile still opens the nav drawer.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/lib/auth/AuthProvider";
import { useUiStore } from "@/lib/shell";

function initialsFor(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "U";
  if (parts.length === 1) return parts[0]!.slice(0, 1).toUpperCase();
  return `${parts[0]!.slice(0, 1)}${parts[1]!.slice(0, 1)}`.toUpperCase();
}

export function Topbar({
  onMenuClick,
}: {
  onMenuClick: () => void;
  /** Kept for call-site compatibility; the Figma shell has no desktop collapse control. */
  onToggleCollapse?: () => void;
  sidebarCollapsed?: boolean;
}) {
  const setCommandPaletteOpen = useUiStore((s) => s.setCommandPaletteOpen);
  const pathname = usePathname();
  const { session, user } = useAuth();
  const signedIn = Boolean(session && user);
  const name = user?.displayName || session?.displayName || "Account";

  return (
    <header
      aria-label="Application header"
      className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--surface)] px-4"
    >
      <div className="flex min-w-0 items-center gap-2.5">
        <button
          type="button"
          className="inline-flex size-9 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] md:hidden"
          onClick={onMenuClick}
          aria-label="Open navigation menu"
        >
          <span aria-hidden>☰</span>
        </button>
        <Link
          href="/dashboard"
          className="flex min-h-9 items-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          <span
            className="dsp-logo-mark"
            style={{ width: 20, height: 20 }}
            aria-hidden
          />
          <span className="font-[family-name:var(--font-display)] text-[15px] tracking-tight text-[var(--fg)]">
            DSP
          </span>
        </Link>
      </div>

      <div className="flex items-center gap-1.5">
        {pathname !== "/diagnostics" ? (
          <Link
            href="/diagnostics"
            className="hidden min-h-9 items-center rounded-lg border border-[var(--border)] px-3.5 text-xs text-[var(--muted)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] sm:inline-flex"
          >
            Diagnostics
          </Link>
        ) : null}
        <button
          type="button"
          className="inline-flex size-9 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          onClick={() => setCommandPaletteOpen(true)}
          aria-label="Open command palette"
          title="Search"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            aria-hidden
          >
            <circle cx="8.5" cy="8.5" r="5.25" />
            <line x1="12.5" y1="12.5" x2="17" y2="17" />
          </svg>
        </button>

        {signedIn ? (
          <Link
            href="/profile"
            aria-label={`${name} — My Profile`}
            className="flex items-center gap-2 rounded-[10px] py-1 pl-1 pr-2.5 hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            <span
              aria-hidden
              className="flex size-[26px] items-center justify-center rounded-full bg-[linear-gradient(135deg,#7c6af7_0%,#2dd4bf_100%)] font-[family-name:var(--font-mono)] text-[10px] font-bold text-white"
            >
              {initialsFor(name)}
            </span>
            <span className="hidden max-w-[10rem] truncate text-[13px] font-medium text-[var(--fg)] md:inline">
              {name}
            </span>
          </Link>
        ) : (
          <Link
            href="/login"
            aria-label="Log in"
            className="rounded-lg border border-[var(--border)] px-3.5 py-1.5 text-[13px] font-medium text-[var(--muted)] hover:border-[var(--c-dsp)] hover:text-[var(--c-dsp)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            Log in
          </Link>
        )}
      </div>
    </header>
  );
}

"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { useAuth } from "@/lib/auth/AuthProvider";

export function ResearchShell({ children }: { children: ReactNode }) {
  const { session } = useAuth();

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">
      <header className="border-b border-[var(--border)] bg-[var(--surface)]/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link
            href="/dashboard"
            className="flex items-center gap-3"
            aria-label="DSP AI Indicator home"
          >
            <span className="grid size-9 place-items-center rounded-[var(--radius-sm)] bg-[var(--accent)] text-sm font-semibold text-[var(--accent-fg)]">
              D
            </span>
            <span>
              <span className="block text-sm font-semibold tracking-[0.08em]">
                DSP AI INDICATOR
              </span>
              <span className="block text-xs text-[var(--muted)]">
                Evidence-first research
              </span>
            </span>
          </Link>
          <nav
            aria-label="Research navigation"
            className="flex items-center gap-2 text-sm"
          >
            <Link
              href="/dashboard"
              className="rounded-[var(--radius-sm)] px-3 py-2 text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
            >
              Search
            </Link>
            {session ? (
              <Link
                href="/logout"
                className="rounded-[var(--radius-sm)] px-3 py-2 text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
              >
                Sign out
              </Link>
            ) : (
              <Link
                href="/login"
                className="rounded-[var(--radius-sm)] bg-[var(--accent)] px-3 py-2 font-medium text-[var(--accent-fg)]"
              >
                Sign in
              </Link>
            )}
          </nav>
        </div>
      </header>
      <main
        id="main-content"
        className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 sm:py-10"
      >
        {children}
      </main>
      <footer className="mx-auto max-w-7xl px-4 pb-8 text-xs text-[var(--muted)] sm:px-6">
        Research tools, not investment advice. Backend-authoritative analysis only.
      </footer>
    </div>
  );
}

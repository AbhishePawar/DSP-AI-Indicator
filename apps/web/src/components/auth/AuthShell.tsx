"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { env } from "@/lib/env";
import { useTheme } from "@/providers/ThemeProvider";

import "./auth.css";

type AuthShellProps = {
  children: ReactNode;
  /** Optional footer note under the card */
  footerNote?: ReactNode;
};

export function AuthShell({ children, footerNote }: AuthShellProps) {
  const { cycleMode, resolved, mode } = useTheme();

  return (
    <div className="relative min-h-screen bg-[var(--bg)] text-[var(--fg)]">
      <div
        className="pointer-events-none absolute inset-0 -z-10"
        aria-hidden="true"
        style={{
          background: `
            radial-gradient(ellipse 80% 55% at 50% 0%, var(--glow), transparent 55%),
            linear-gradient(180deg, var(--bg) 0%, var(--surface-2) 100%)
          `,
        }}
      />

      <header className="mx-auto flex max-w-[72rem] items-center justify-between gap-3 px-4 py-4 sm:px-6">
        <Link
          href="/"
          className="font-[family-name:var(--font-display)] text-lg font-medium tracking-tight focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
        >
          {env.appName}
        </Link>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={cycleMode}
            className="rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-xs text-[var(--muted)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
            aria-label={`Theme: ${mode}. Activate to cycle. Showing ${resolved}.`}
          >
            {resolved === "dark" ? "Dark" : "Light"}
          </button>
          <Link
            href="/"
            className="hidden text-sm text-[var(--muted)] underline-offset-2 hover:underline sm:inline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            Marketing site
          </Link>
        </div>
      </header>

      <div className="mx-auto flex min-h-[calc(100vh-8rem)] max-w-[72rem] items-center justify-center px-4 pb-12 sm:px-6">
        <div className="auth-reveal w-full max-w-md">{children}</div>
      </div>

      {footerNote ? (
        <p className="pb-8 text-center text-xs text-[var(--muted)]">
          {footerNote}
        </p>
      ) : (
        <p className="pb-8 text-center text-xs text-[var(--muted)]">
          Research Mode by default · Not investment advice
        </p>
      )}
    </div>
  );
}

export function AuthCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-lg)] sm:p-8">
      <h1 className="font-[family-name:var(--font-display)] text-2xl font-medium tracking-tight text-[var(--fg)] sm:text-3xl">
        {title}
      </h1>
      {description ? (
        <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">
          {description}
        </p>
      ) : null}
      <div className="mt-6">{children}</div>
    </div>
  );
}

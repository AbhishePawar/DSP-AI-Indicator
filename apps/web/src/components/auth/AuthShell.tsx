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
    <div className="flex min-h-screen bg-[var(--bg)] text-[var(--fg)]">
      <aside className="hidden w-[420px] shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface)] px-10 py-12 lg:flex">
        <Link
          href="/"
          className="flex items-center gap-2.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
        >
          <span className="dsp-logo-mark" aria-hidden />
          <span className="font-[family-name:var(--font-display)] text-xl tracking-tight">
            DSP
          </span>
        </Link>
        <div className="flex flex-1 flex-col justify-center gap-8">
          <div>
            <h2 className="font-[family-name:var(--font-display)] text-3xl font-medium leading-tight tracking-tight">
              Research-grade
              <br />
              AI for every investor.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-[var(--muted)]">
              Ask DSP anything about any listed company. Official evidence
              through the deterministic DSP pipeline. No invented numbers.
            </p>
          </div>
          {[
            "Chat-first equity research",
            "Official evidence before opinion",
            "Deterministic DSP calculations",
            "Thin-client /api/v1 only",
          ].map((feature) => (
            <div key={feature} className="flex items-center gap-2.5">
              <span className="text-sm text-[var(--c-profit)]" aria-hidden>
                ✓
              </span>
              <span className="text-sm text-[var(--muted)]">{feature}</span>
            </div>
          ))}
        </div>
        <p className="font-mono text-[11px] text-[var(--muted)]">
          © {new Date().getFullYear()} {env.appName}
        </p>
      </aside>

      <div className="relative flex min-w-0 flex-1 flex-col">
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
        <header className="flex items-center justify-between gap-3 px-4 py-4 sm:px-6 lg:justify-end">
          <Link
            href="/"
            className="flex items-center gap-2 font-[family-name:var(--font-display)] text-lg font-medium tracking-tight focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] lg:hidden"
          >
            <span className="dsp-logo-mark" aria-hidden />
            DSP
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

        <div className="mx-auto flex min-h-[calc(100vh-8rem)] w-full max-w-[400px] flex-1 items-center px-4 pb-12 sm:px-6">
          <div className="auth-reveal w-full">{children}</div>
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
    <div>
      <h1 className="font-[family-name:var(--font-display)] text-[28px] font-medium tracking-tight text-[var(--fg)]">
        {title}
      </h1>
      {description ? (
        <p className="mt-1.5 text-sm leading-relaxed text-[var(--muted)]">
          {description}
        </p>
      ) : null}
      <div className="mt-8">{children}</div>
    </div>
  );
}

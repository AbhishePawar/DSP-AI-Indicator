"use client";

import Link from "next/link";

import { LandingResearchSearch } from "@/components/marketing/LandingResearchSearch";

const FEATURES = [
  {
    href: "/copilot",
    title: "Conversational Research",
    description:
      "Ask a question and continue in the research copilot. Answers stay tied to the authenticated DSP pipeline.",
    accent: "var(--c-dsp)",
  },
  {
    href: "/analysis",
    title: "Visual Evidence",
    description:
      "Open a company analysis with charts and evidence from the statements and quote services when they are available.",
    accent: "var(--c-revenue)",
  },
  {
    href: "/analysis",
    title: "DSP Analysis",
    description:
      "Business quality, valuation, and risks are shown only when the deterministic analysis response includes them.",
    accent: "var(--c-dsp)",
  },
  {
    href: "/analysis/compare",
    title: "Peer Comparison",
    description:
      "Compare companies through the existing comparison workspace. Missing peers stay unavailable.",
    accent: "var(--c-profit)",
  },
] as const;

export function MarketingLanding() {
  return (
    <div>
      <section className="mx-auto flex max-w-3xl flex-col items-center px-4 pb-16 pt-16 text-center sm:px-6 sm:pt-24 md:pt-28">
        <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 font-mono text-[11px] tracking-wide text-[var(--muted)]">
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" aria-hidden />
          Official evidence · deterministic DSP
        </p>
        <h1
          id="hero-brand"
          className="font-[family-name:var(--font-heading)] text-4xl font-medium leading-[1.05] tracking-tight text-[var(--fg)] sm:text-5xl md:text-6xl"
        >
          Ask DSP anything
          <br />
          about any company.
        </h1>
        <p className="mt-5 max-w-xl text-base leading-relaxed text-[var(--muted)] sm:text-lg">
          Search a listed company, then open simple research or the full DSP
          analysis. Figures appear only when the authenticated services return them.
        </p>
        <div className="mt-10 w-full">
          <LandingResearchSearch />
        </div>
      </section>

      <section
        id="features"
        aria-labelledby="features-heading"
        className="mx-auto max-w-5xl px-4 py-16 sm:px-6"
      >
        <h2
          id="features-heading"
          className="text-center font-[family-name:var(--font-heading)] text-3xl font-medium text-[var(--fg)] sm:text-4xl"
        >
          Everything you need to research.
        </h2>
        <p className="mx-auto mt-3 max-w-lg text-center text-sm leading-relaxed text-[var(--muted)]">
          The same workspaces used after sign-in: copilot, company analysis, and comparison.
        </p>
        <div className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-2">
          {FEATURES.map((feature) => (
            <Link
              key={feature.title}
              href={feature.href}
              className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 text-left transition-colors hover:border-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              <span
                className="mb-4 block h-0.5 w-8 rounded-full"
                style={{ background: feature.accent }}
                aria-hidden
              />
              <h3 className="text-base font-medium text-[var(--fg)]">{feature.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">
                {feature.description}
              </p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

import Link from "next/link";

import { FEATURES, TRUST_PILLARS, WORKFLOW_STEPS } from "./content";
import { MarketingHeader } from "./MarketingHeader";
import { Section } from "./Section";

export function MarketingLanding() {
  return (
    <main className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">
      <MarketingHeader />
      <Section title="Complex analysis. Simple decisions." className="grid gap-10 py-20 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <div className="flex flex-col gap-6">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--accent)]">DSP AI Indicator</p>
          <h1 className="max-w-3xl text-pretty text-5xl font-semibold tracking-tight sm:text-6xl">Complex analysis. Simple decisions.</h1>
          <p className="max-w-2xl text-lg leading-8 text-[var(--muted)]">Institutional investment research with evidence, explainability, governed AI, and calm decision support.</p>
          <div className="flex flex-wrap gap-3">
            <Link className="rounded-md bg-[var(--accent)] px-5 py-3 font-semibold text-white" href="/analysis">Open research workspace</Link>
            <Link className="rounded-md border border-[var(--border)] px-5 py-3 font-semibold" href="#features">Explore the platform</Link>
          </div>
        </div>
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
          <p className="text-sm font-semibold text-[var(--muted)]">Research standard</p>
          <p className="mt-4 text-2xl font-semibold">Evidence before ornament.</p>
          <p className="mt-3 leading-7 text-[var(--muted)]">Every material insight identifies what it means, why it matters, and what should be investigated next.</p>
        </div>
      </Section>
      <Section id="features" title="A research desk built for accountability." className="flex flex-col gap-8 py-16">
        <h2 className="text-3xl font-semibold">A research desk built for accountability.</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => <article className="rounded-xl border border-[var(--border)] p-5" key={feature.title}><h3 className="font-semibold">{feature.title}</h3><p className="mt-2 leading-7 text-[var(--muted)]">{feature.body}</p></article>)}
        </div>
      </Section>
      <Section id="trust" title="Trust by design." className="grid gap-8 py-16 md:grid-cols-2">
        {TRUST_PILLARS.map((pillar) => <article key={pillar.title}><h3 className="text-xl font-semibold">{pillar.title}</h3><p className="mt-2 leading-7 text-[var(--muted)]">{pillar.body}</p></article>)}
      </Section>
      <Section id="workflow" title="From evidence to review." className="flex flex-col gap-6 py-16">
        <h2 className="text-3xl font-semibold">From evidence to review.</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {WORKFLOW_STEPS.map((step) => <article className="rounded-xl bg-[var(--surface)] p-5" key={step.step}><p className="text-sm font-semibold text-[var(--accent)]">{step.step}</p><h3 className="mt-4 font-semibold">{step.title}</h3><p className="mt-2 leading-7 text-[var(--muted)]">{step.body}</p></article>)}
        </div>
      </Section>
    </main>
  );
}

export default MarketingLanding;

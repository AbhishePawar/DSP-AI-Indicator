import Link from "next/link";

import {
  COMMERCIAL_PRICING_DISCLOSURE,
  PRODUCT_EDITIONS,
  SUPPORT_CONTACT,
} from "@/lib/commercial";
import { env } from "@/lib/env";

import {
  ABOUT_PARAGRAPHS,
  FAQ_ITEMS,
  FEATURES,
  TRUST_PILLARS,
  WORKFLOW_STEPS,
} from "./content";
import { Section } from "./Section";

function formatPrice(edition: (typeof PRODUCT_EDITIONS)[number]): string {
  if (edition.monthlyPriceUsd === null) return "Contact for access";
  if (edition.monthlyPriceUsd === 0) {
    return "Illustrative · not available for purchase";
  }
  return `Illustrative · $${edition.monthlyPriceUsd}/mo · not available for purchase`;
}

export function MarketingLanding() {
  return (
    <>
      {/* Hero — one composition: brand, headline, sentence, CTAs, full-bleed wash */}
      <section
        className="relative isolate min-h-[min(92vh,52rem)] overflow-hidden"
        aria-labelledby="hero-brand"
      >
        <div
          className="mkt-hero-wash pointer-events-none absolute inset-0 -z-10"
          aria-hidden="true"
          style={{
            background: `
              radial-gradient(ellipse 90% 70% at 70% 20%, var(--glow), transparent 55%),
              linear-gradient(165deg, var(--bg) 0%, var(--surface-2) 48%, var(--bg) 100%)
            `,
          }}
        />
        <div className="mx-auto flex max-w-[72rem] flex-col justify-end px-4 pb-16 pt-20 sm:px-6 sm:pb-24 sm:pt-28">
          <h1
            id="hero-brand"
            className="mkt-reveal font-[family-name:var(--font-display)] text-5xl font-medium tracking-tight text-[var(--fg)] sm:text-6xl md:text-7xl"
          >
            {env.appName}
          </h1>
          <p className="mkt-reveal mkt-reveal-delay mt-6 max-w-[28ch] font-[family-name:var(--font-display)] text-2xl font-medium tracking-tight text-[var(--fg)] sm:text-3xl">
            {env.tagline}
          </p>
          <p className="mkt-fade mt-4 max-w-[42ch] text-base leading-relaxed text-[var(--muted)] sm:text-lg">
            Institutional investment research with evidence, explainability, and
            governed AI — calm enough for serious work.
          </p>
          <div className="mkt-fade mt-10 flex flex-wrap gap-3">
            <Link
              href="/login"
              className="inline-flex min-h-11 items-center rounded-[var(--radius-sm)] bg-[var(--accent)] px-5 py-2.5 text-sm font-medium text-[var(--accent-fg)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="inline-flex min-h-11 items-center rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-5 py-2.5 text-sm text-[var(--fg)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
            >
              Create account
            </Link>
          </div>
        </div>
      </section>

      <Section
        id="features"
        eyebrow="Capabilities"
        title="Research tools without tip-app noise"
        lead="Six capabilities that keep analysis inspectable — from workspace to governance."
      >
        <ul className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <li key={feature.title} className="max-w-[40ch]">
              <h3 className="font-[family-name:var(--font-display)] text-xl font-medium tracking-tight">
                {feature.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">
                {feature.body}
              </p>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        id="philosophy"
        eyebrow="Research philosophy"
        title="Evidence before opinion"
        lead="DSP treats research as an institutional discipline: truth, evidence, and confidence stay distinct. AI interprets — it does not invent certainty."
      >
        <ul className="grid gap-6 md:grid-cols-3">
          {[
            {
              t: "Ontology-backed language",
              d: "REP-002 meanings keep quality, risk, valuation, and decisions from collapsing into slogans.",
            },
            {
              t: "Thin client",
              d: "Browsers present frozen API outcomes. Valuation and recommendation reasoning stay server-side.",
            },
            {
              t: "Long-horizon calm",
              d: "The interface prefers clarity over urgency — suitable for desks that measure in years.",
            },
          ].map((item) => (
            <li
              key={item.t}
              className="border-l-2 border-[var(--accent)] pl-4"
            >
              <h3 className="font-[family-name:var(--font-display)] text-lg font-medium">
                {item.t}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">
                {item.d}
              </p>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        id="trust"
        eyebrow="Trust framework"
        title="Trust is the product feature"
        lead="Every visible insight should be traceable, explainable, consistent, actionable, and honest."
      >
        <ul className="grid gap-8 sm:grid-cols-2">
          {TRUST_PILLARS.map((pillar) => (
            <li key={pillar.title}>
              <h3 className="font-[family-name:var(--font-display)] text-xl font-medium tracking-tight">
                {pillar.title}
              </h3>
              <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-[var(--muted)]">
                {pillar.body}
              </p>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        id="ai-committee"
        eyebrow="AI Committee"
        title="Governed interpretation, not opaque tips"
        lead="The AI Committee is the institutional construct for reviewing AI-mediated research language — with explainability, traceability, and human oversight."
      >
        <div className="grid gap-8 lg:grid-cols-2">
          <p className="max-w-[56ch] text-sm leading-relaxed text-[var(--muted)]">
            Raw data, calculated metrics, AI interpretation, and street opinion
            remain separated in presentation. Committee outcomes are reviewable;
            they do not silently become brokerage instructions.
          </p>
          <ul className="space-y-3 text-sm text-[var(--fg)]">
            <li className="flex gap-2">
              <span className="text-[var(--accent)]" aria-hidden="true">
                —
              </span>
              Explicit confidence and disclosure
            </li>
            <li className="flex gap-2">
              <span className="text-[var(--accent)]" aria-hidden="true">
                —
              </span>
              Challenge paths for contradictory evidence
            </li>
            <li className="flex gap-2">
              <span className="text-[var(--accent)]" aria-hidden="true">
                —
              </span>
              Human oversight when stakes or uncertainty rise
            </li>
          </ul>
        </div>
      </Section>

      <Section
        id="valuation"
        eyebrow="Valuation engine"
        title="Value with range and humility"
        lead="Valuation vocabulary covers intrinsic value, margins of safety, scenarios, and valuation confidence — presented with assumptions, not theatre."
      >
        <p className="max-w-[60ch] text-sm leading-relaxed text-[var(--muted)]">
          The marketing surface explains the capability. Computation stays in
          backend engines. Users see transparent ranges, method context, and
          confidence labels aligned to the Institutional Design System and
          Research Mode.
        </p>
      </Section>

      <Section
        id="business-quality"
        eyebrow="Business quality"
        title="Durability beyond the ticker tape"
        lead="Quality analysis examines competitive position, pricing power, capital allocation, and deterioration signals — independent of short-term price moves."
      >
        <p className="max-w-[60ch] text-sm leading-relaxed text-[var(--muted)]">
          Management quality and economic moat concepts remain first-class
          research meanings, referenced without collapsing into a single vanity
          score.
        </p>
      </Section>

      <Section
        id="workflow"
        eyebrow="Research workflow"
        title="From evidence to revisable conclusions"
        lead="A calm four-stage path that matches how institutional research should move."
      >
        <ol className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {WORKFLOW_STEPS.map((item) => (
            <li key={item.step}>
              <p className="text-xs font-medium text-[var(--accent)]">
                {item.step}
              </p>
              <h3 className="mt-2 font-[family-name:var(--font-display)] text-lg font-medium">
                {item.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">
                {item.body}
              </p>
            </li>
          ))}
        </ol>
      </Section>

      <Section
        id="pricing"
        eyebrow="Pricing"
        title="Editions for desks of every scale"
        lead="Illustrative edition packaging for planning only — not available for public purchase on this release."
      >
        <p
          role="note"
          className="mb-6 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-sm text-[var(--muted)]"
        >
          {COMMERCIAL_PRICING_DISCLOSURE}
        </p>
        <ul className="grid gap-6 lg:grid-cols-3">
          {PRODUCT_EDITIONS.map((edition) => (
            <li
              key={edition.id}
              className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-6"
            >
              <h3 className="font-[family-name:var(--font-display)] text-xl font-medium">
                {edition.name}
              </h3>
              <p className="mt-1 text-sm text-[var(--muted)]">{edition.tagline}</p>
              <p className="mt-4 font-[family-name:var(--font-display)] text-2xl font-medium">
                {formatPrice(edition)}
              </p>
              <p className="mt-2 text-sm text-[var(--muted)]">{edition.audience}</p>
            </li>
          ))}
        </ul>
        <p className="mt-6 text-sm">
          <Link className="text-[var(--accent)] underline" href="/pricing">
            View full pricing and feature matrix
          </Link>
        </p>
      </Section>

      <Section
        id="faq"
        eyebrow="FAQ"
        title="Clear answers before you sign in"
        lead="Common questions about advice boundaries, architecture, and access."
      >
        <dl className="mx-auto max-w-3xl space-y-6">
          {FAQ_ITEMS.map((item) => (
            <div key={item.q}>
              <dt className="font-[family-name:var(--font-display)] text-lg font-medium">
                {item.q}
              </dt>
              <dd className="mt-2 text-sm leading-relaxed text-[var(--muted)]">
                {item.a}
              </dd>
            </div>
          ))}
        </dl>
        <p className="mt-8 text-sm">
          <Link className="text-[var(--accent)] underline" href="/faq">
            Open full FAQ
          </Link>
        </p>
      </Section>

      <Section
        id="about-preview"
        eyebrow="About"
        title="A quiet research desk for serious work"
        lead={ABOUT_PARAGRAPHS[0]}
      >
        <Link className="text-sm text-[var(--accent)] underline" href="/about">
          Read about DSP
        </Link>
      </Section>

      <Section
        id="auth"
        eyebrow="Access"
        title="Sign in or create an account"
        lead="Create a DSP AI Indicator account with your name, mobile, username, and Gmail — or continue with Google. Existing users can sign in."
      >
        <div className="flex flex-wrap gap-3">
          <Link
            href="/login"
            className="inline-flex min-h-11 items-center rounded-[var(--radius-sm)] bg-[var(--accent)] px-5 py-2.5 text-sm font-medium text-[var(--accent-fg)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            Sign in
          </Link>
          <Link
            href="/register"
            className="inline-flex min-h-11 items-center rounded-[var(--radius-sm)] border border-[var(--border)] px-5 py-2.5 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            Create account
          </Link>
          <Link
            href="/contact"
            className="inline-flex min-h-11 items-center px-2 text-sm text-[var(--muted)] underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            Contact
          </Link>
        </div>
      </Section>
    </>
  );
}

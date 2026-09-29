import type { Metadata } from "next";

import { ABOUT_PARAGRAPHS } from "@/components/marketing";
import { env } from "@/lib/env";

export const metadata: Metadata = {
  title: "About",
  description: `About ${env.appName} — institutional research philosophy and product mission.`,
  alternates: { canonical: "/about" },
};

export default function AboutPage() {
  return (
    <div>
      <section className="mx-auto max-w-[760px] px-4 py-16 text-center sm:px-6 sm:py-20">
        <h1 className="font-[family-name:var(--font-heading)] text-[clamp(32px,5vw,52px)] font-medium leading-[1.15] tracking-tight text-[var(--fg)]">
          Making serious equity research
          <br />
          understandable without invented numbers.
        </h1>
        <p className="mx-auto mt-5 max-w-[520px] text-base leading-relaxed text-[var(--muted)]">
          {ABOUT_PARAGRAPHS[0]}
        </p>
      </section>

      <section className="border-y border-[var(--border)] bg-[var(--surface)] px-4 py-16 sm:px-6">
        <div className="mx-auto grid max-w-[760px] gap-10 md:grid-cols-2 md:gap-12">
          <div>
            <h2 className="font-[family-name:var(--font-heading)] text-[26px] font-medium text-[var(--fg)]">
              Our mission
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-[var(--muted)]">
              {ABOUT_PARAGRAPHS[1]}
            </p>
          </div>
          <div>
            <h2 className="font-[family-name:var(--font-heading)] text-[26px] font-medium text-[var(--fg)]">
              How analysis is shown
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-[var(--muted)]">
              {ABOUT_PARAGRAPHS[2]}
            </p>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-[800px] grid-cols-1 gap-8 px-4 py-14 text-center sm:grid-cols-3 sm:px-6">
        {[
          ["Founded", "Data unavailable."],
          ["Securities covered", "Data unavailable."],
          ["Published team", "Data unavailable."],
        ].map(([label, value]) => (
          <div key={label}>
            <p className="font-[family-name:var(--font-heading)] text-2xl text-[var(--c-dsp)]">
              {value}
            </p>
            <p className="mt-2 font-mono text-xs uppercase tracking-wider text-[var(--muted)]">
              {label}
            </p>
          </div>
        ))}
      </section>
    </div>
  );
}

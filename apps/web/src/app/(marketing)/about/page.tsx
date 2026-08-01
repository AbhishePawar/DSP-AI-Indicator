import type { Metadata } from "next";
import Link from "next/link";

import { ABOUT_PARAGRAPHS, Section } from "@/components/marketing";
import { env } from "@/lib/env";

export const metadata: Metadata = {
  title: "About",
  description: `About ${env.appName} — institutional research philosophy and product mission.`,
  alternates: { canonical: "/about" },
};

export default function AboutPage() {
  return (
    <Section
      id="about"
      eyebrow="About"
      title={`${env.appName}`}
      lead="A quiet institutional research desk for evidence-first investment analysis."
    >
      <div className="max-w-[62ch] space-y-4 text-base leading-relaxed text-[var(--muted)]">
        {ABOUT_PARAGRAPHS.map((p) => (
          <p key={p}>{p}</p>
        ))}
        <p>
          Brand promise: <strong className="text-[var(--fg)]">{env.tagline}</strong>{" "}
          · Professional Investment Research for Everyone.
        </p>
      </div>
      <p className="mt-8 text-sm">
        <Link className="text-[var(--accent)] underline" href="/contact">
          Contact us
        </Link>
        {" · "}
        <Link className="text-[var(--accent)] underline" href="/login">
          Sign in
        </Link>
      </p>
    </Section>
  );
}

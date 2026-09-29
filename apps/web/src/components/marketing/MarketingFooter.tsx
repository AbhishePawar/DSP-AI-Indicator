import Link from "next/link";

import { env } from "@/lib/env";

const LINKS = [
  { href: "/about", label: "About" },
  { href: "/pricing", label: "Pricing" },
  { href: "/faq", label: "FAQ" },
  { href: "/contact", label: "Contact" },
  { href: "/docs/privacy", label: "Privacy" },
  { href: "/docs/terms", label: "Terms" },
  { href: "/docs/disclaimer", label: "Disclaimer" },
] as const;

export function MarketingFooter() {
  return (
    <footer className="border-t border-[var(--border)] px-4 py-8 sm:px-12">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="font-[family-name:var(--font-heading)] text-base text-[var(--muted)]">
          DSP AI Indicator
          <span className="sr-only">{env.appName}</span>
        </p>
        <p className="font-mono text-xs text-[var(--muted)]">
          © {new Date().getFullYear()} · Research use, not investment advice
        </p>
      </div>
      <nav aria-label="Footer" className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-sm">
        {LINKS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="inline-flex min-h-11 items-center text-[var(--muted)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </footer>
  );
}

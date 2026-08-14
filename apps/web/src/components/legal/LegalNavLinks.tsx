"use client";

import Link from "next/link";

import { LEGAL_ROUTES } from "@/lib/legal";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: LEGAL_ROUTES.privacy, label: "Privacy Policy" },
  { href: LEGAL_ROUTES.terms, label: "Terms of Service" },
  { href: LEGAL_ROUTES.disclaimer, label: "Disclaimer" },
  { href: "/docs/support", label: "Support" },
] as const;

/** Compact legal + support links for header / footer (P4.1 + P6.1). */
export function LegalNavLinks({
  className,
  density = "footer",
}: {
  className?: string;
  density?: "footer" | "header";
}) {
  const textClass =
    density === "header"
      ? "text-[11px] text-[var(--muted)] hover:text-[var(--fg)]"
      : "text-[10px] text-[var(--muted)] underline-offset-2 hover:underline hover:text-[var(--fg)]";

  return (
    <nav
      className={cn("flex flex-wrap items-center gap-x-2 gap-y-1", className)}
      aria-label="Legal and support"
    >
      {LINKS.map((link, i) => (
        <span key={link.href} className="inline-flex items-center gap-2">
          {i > 0 ? (
            <span className="text-[var(--border)]" aria-hidden>
              ·
            </span>
          ) : null}
          <Link href={link.href} className={textClass}>
            {link.label}
          </Link>
        </span>
      ))}
    </nav>
  );
}

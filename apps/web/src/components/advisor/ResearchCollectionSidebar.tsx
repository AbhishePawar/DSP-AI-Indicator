"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const RESEARCH_LINKS: ReadonlyArray<{
  href: string;
  label: string;
  exact?: boolean;
}> = [
  { href: "/advisor/research", label: "Library", exact: true },
  { href: "/advisor/research/collections", label: "Collections" },
  { href: "/advisor/research/compare", label: "Compare" },
  { href: "/advisor/research/notes", label: "Notes" },
  { href: "/advisor/research/timeline", label: "Timeline" },
  { href: "/advisor/research/bookmarks", label: "Bookmarks" },
];

export function ResearchCollectionSidebar() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Advisor research sections"
      className="flex flex-wrap gap-1 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-2 lg:w-44 lg:shrink-0 lg:flex-col"
    >
      {RESEARCH_LINKS.map((link) => {
        const active = link.exact
          ? pathname === link.href
          : pathname === link.href || pathname.startsWith(`${link.href}/`);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            className={`min-h-11 rounded-md px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
              active
                ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}

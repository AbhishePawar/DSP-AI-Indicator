"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const REVIEW_LINKS: ReadonlyArray<{
  href: string;
  label: string;
  exact?: boolean;
}> = [
  { href: "/advisor/reviews", label: "Workspace", exact: true },
  { href: "/advisor/reviews/dashboard", label: "Dashboard" },
  { href: "/advisor/reviews/active", label: "Active Review" },
  { href: "/advisor/reviews/templates", label: "Templates" },
];

export function ReviewSidebar() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Client review sections"
      className="flex flex-wrap gap-1 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-2 lg:w-44 lg:shrink-0 lg:flex-col"
    >
      {REVIEW_LINKS.map((link) => {
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

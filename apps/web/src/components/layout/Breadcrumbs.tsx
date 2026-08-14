"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbSeparator,
} from "@/components/ds";
import { breadcrumbsForPath, useUiStore } from "@/lib/shell";

export function Breadcrumbs() {
  const pathname = usePathname();
  const crumbs = breadcrumbsForPath(pathname);
  const recordRecentPage = useUiStore((s) => s.recordRecentPage);

  useEffect(() => {
    const current = crumbs[crumbs.length - 1];
    if (current) {
      recordRecentPage(pathname, current.label);
    }
  }, [pathname, recordRecentPage]); // eslint-disable-line react-hooks/exhaustive-deps -- record on path change only

  return (
    <Breadcrumb className="text-xs">
      {crumbs.map((crumb, i) => {
        const last = i === crumbs.length - 1;
        return (
          <span key={`${crumb.href}-${i}`} className="contents">
            {i > 0 ? <BreadcrumbSeparator /> : null}
            {last ? (
              <BreadcrumbItem current>{crumb.label}</BreadcrumbItem>
            ) : (
              <li className="inline-flex items-center">
                <Link
                  href={crumb.href}
                  className="rounded-sm text-[var(--muted)] transition hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                >
                  {crumb.label}
                </Link>
              </li>
            )}
          </span>
        );
      })}
    </Breadcrumb>
  );
}

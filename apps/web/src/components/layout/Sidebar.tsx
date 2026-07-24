"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { getPrimaryNav } from "@/lib/navigation";
import { env } from "@/lib/env";

export function Sidebar({
  collapsed,
  onNavigate,
  mobile = false,
}: {
  collapsed: boolean;
  onNavigate?: () => void;
  mobile?: boolean;
}) {
  const pathname = usePathname();
  const nav = getPrimaryNav();

  return (
    <aside
      className={`${
        mobile
          ? "flex h-full w-72 flex-col"
          : `hidden md:flex md:flex-col md:border-r md:border-[var(--border)] md:bg-[var(--surface)] ${
              collapsed ? "md:w-[4.5rem]" : "md:w-60"
            }`
      } shrink-0 transition-[width] duration-200`}
      aria-label="Primary"
    >
      <div
        className={`border-b border-[var(--border)] px-3 py-4 ${
          collapsed && !mobile ? "px-2 text-center" : ""
        }`}
      >
        <Link
          href="/dashboard"
          onClick={onNavigate}
          className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          <p
            className={`font-[family-name:var(--font-display)] tracking-tight text-[var(--accent)] ${
              collapsed && !mobile ? "text-sm" : "text-lg"
            }`}
          >
            {collapsed && !mobile ? "DSP" : env.appName}
          </p>
          {!(collapsed && !mobile) ? (
            <p className="mt-0.5 text-xs text-[var(--muted)]">
              Complex Analysis. Simple Decisions.
            </p>
          ) : null}
        </Link>
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2" aria-label="Main">
        {nav.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.label}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-2 rounded-md px-2.5 py-2 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                active
                  ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                  : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
              } ${collapsed && !mobile ? "justify-center" : ""}`}
            >
              <span
                className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${
                  active ? "bg-[var(--accent)]" : "bg-[var(--border)]"
                }`}
                aria-hidden
              />
              {!(collapsed && !mobile) ? <span>{item.label}</span> : null}
              {collapsed && !mobile ? (
                <span className="sr-only">{item.label}</span>
              ) : null}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

"use client";

import {
  LayoutDashboard,
  Building2,
  Briefcase,
  BookOpen,
  Shield,
  Settings,
  Sparkles,
  User,
  Users,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState, type KeyboardEvent } from "react";

import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";

import { useAuth } from "@/lib/auth/AuthProvider";
import { env } from "@/lib/env";
import {
  filterShellNav,
  isActivePath,
  zipSidebarModel,
  type ShellNavIconId,
  type ShellNavItem,
} from "@/lib/shell";
import { cn } from "@/lib/utils";

const ICONS: Record<ShellNavIconId, LucideIcon> = {
  dashboard: LayoutDashboard,
  analysis: Building2,
  portfolio: Briefcase,
  research: BookOpen,
  admin: Shield,
  settings: Settings,
  profile: User,
  copilot: Sparkles,
  advisor: Users,
};

const ZIP_GLYPH: Record<string, string> = {
  dashboard: "⬡",
  research: "◈",
  companies: "⊞",
  compare: "⇌",
  portfolio: "◲",
  copilot: "✦",
  advisor: "◑",
  profile: "◎",
  coupons: "◈",
  pricing: "◇",
  "control-center": "⚙",
  admin: "⊕",
  diagnostics: "◎",
};

function displayLabel(item: ShellNavItem): string {
  if (item.id === "admin") return "Admin";
  if (item.id === "research") return "Research";
  return item.label;
}

function SearchGlyph() {
  return (
    <svg
      width="17"
      height="17"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      aria-hidden
    >
      <circle cx="8.5" cy="8.5" r="5.25" />
      <line x1="12.5" y1="12.5" x2="17" y2="17" />
    </svg>
  );
}

function NavLink({
  item,
  collapsed,
  mobile,
  onNavigate,
  exact = false,
  iconOnly = false,
  dot = false,
}: {
  item: ShellNavItem;
  collapsed: boolean;
  mobile: boolean;
  onNavigate?: () => void;
  exact?: boolean;
  iconOnly?: boolean;
  dot?: boolean;
}) {
  const pathname = usePathname();
  const active = exact
    ? pathname === item.href
    : isActivePath(pathname, item.href);
  const Icon = ICONS[item.icon];
  const label = displayLabel(item);
  const hideLabel = iconOnly || (collapsed && !mobile);
  const glyph = ZIP_GLYPH[item.id];

  return (
    <Link
      href={item.href}
      title={label}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={cn(
        "inline-flex items-center gap-2.5 rounded-lg px-2.5 text-[13px] transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] motion-reduce:transition-none",
        mobile ? "min-h-11" : "min-h-9 py-1.5",
        hideLabel
          ? mobile
            ? "min-w-11 justify-center px-0"
            : "w-9 justify-center px-0"
          : "justify-start",
        dot && !hideLabel ? "text-xs" : null,
        active
          ? "bg-[var(--surface-2)] text-[var(--fg)]"
          : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
      )}
    >
      {item.id === "research" && iconOnly ? (
        <SearchGlyph />
      ) : dot && !hideLabel ? (
        <span
          aria-hidden
          className="ml-1 size-1 shrink-0 rounded-full bg-current"
        />
      ) : glyph && !hideLabel ? (
        <span aria-hidden className="w-4 text-center text-sm opacity-80">
          {glyph}
        </span>
      ) : (
        <Icon className="size-4 shrink-0" aria-hidden />
      )}
      {!hideLabel ? <span className="truncate">{label}</span> : null}
      {hideLabel ? <span className="sr-only">{label}</span> : null}
    </Link>
  );
}

export function Sidebar({
  collapsed,
  onNavigate,
  mobile = false,
}: {
  collapsed: boolean;
  onNavigate?: () => void;
  mobile?: boolean;
}) {
  const { session, user } = useAuth();
  const permissions = session?.permissions ?? user?.permissions ?? [];
  const roles = session?.roles ?? user?.roles ?? [];
  const [recent, setRecent] = useState<RecentAnalysisEntry[]>([]);

  useEffect(() => {
    setRecent(loadRecentAnalyses());
  }, []);

  const nav = useMemo(() => {
    return zipSidebarModel(filterShellNav(permissions, roles));
  }, [permissions, roles]);

  function onNavKeyDown(event: KeyboardEvent<HTMLElement>) {
    const root = event.currentTarget;
    const links = Array.from(
      root.querySelectorAll<HTMLAnchorElement>("a[href]"),
    );
    if (!links.length) return;
    const index = links.indexOf(document.activeElement as HTMLAnchorElement);
    if (event.key === "ArrowDown") {
      event.preventDefault();
      const next = links[(index + 1 + links.length) % links.length];
      next?.focus();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      const prev = links[(index - 1 + links.length) % links.length];
      prev?.focus();
    } else if (event.key === "Home") {
      event.preventDefault();
      links[0]?.focus();
    } else if (event.key === "End") {
      event.preventDefault();
      links[links.length - 1]?.focus();
    }
  }

  return (
    <aside
      className={cn(
        "shrink-0 transition-[width] duration-200 motion-reduce:transition-none",
        mobile
          ? "flex h-full w-72 flex-col"
          : cn(
              "hidden h-full overflow-hidden md:flex md:flex-col md:border-r md:border-[var(--border)] md:bg-[var(--surface)]",
              collapsed ? "md:w-[4.5rem]" : "md:w-[220px]",
            ),
      )}
      aria-label="Primary"
      data-collapsed={collapsed && !mobile ? "true" : undefined}
      onKeyDown={onNavKeyDown}
    >
      <div
        className={cn(
          "border-b border-[var(--border)] px-3 py-4",
          collapsed && !mobile ? "px-2 text-center" : "",
        )}
      >
        <Link
          href="/"
          onClick={onNavigate}
          className="flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          <span className="dsp-logo-mark" aria-hidden />
          {!(collapsed && !mobile) ? (
            <span>
              <p className="font-[family-name:var(--font-display)] text-lg tracking-tight text-[var(--fg)]">
                DSP
              </p>
              <p className="font-mono text-[10px] tracking-[0.06em] text-[var(--muted)]">
                AI RESEARCH
              </p>
            </span>
          ) : (
            <span className="sr-only">{env.appName}</span>
          )}
        </Link>
      </div>

      {!(collapsed && !mobile) ? (
        <div className="border-b border-[var(--border)] px-3 py-3">
          <Link
            href="/analysis"
            onClick={onNavigate}
            className="flex min-h-11 w-full items-center gap-2 rounded-[10px] border border-[var(--border)] bg-[var(--surface-2)] px-3 text-sm font-medium text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            <span aria-hidden className="text-base text-[var(--muted)]">
              +
            </span>
            Start New Research
          </Link>
          <p className="section-label mt-3 mb-1">Today</p>
          {recent.length === 0 ? (
            <p className="px-1 text-xs text-[var(--muted)]">No recent research.</p>
          ) : (
            <ul className="space-y-0.5">
              {recent.slice(0, 3).map((entry) => (
                <li key={`${entry.ticker}-${entry.analysedAt}`}>
                  <Link
                    href={`/analysis?symbol=${encodeURIComponent(entry.ticker)}`}
                    onClick={onNavigate}
                    className="block truncate rounded-lg px-2 py-1.5 text-xs text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                  >
                    {entry.company || entry.ticker}
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <Link
            href="/analysis"
            onClick={onNavigate}
            className="mt-3 flex items-center justify-between rounded-[var(--card-radius)] border border-[color-mix(in_srgb,var(--c-cashflow)_30%,transparent)] bg-[color-mix(in_srgb,var(--c-cashflow)_12%,transparent)] px-3.5 py-3 no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            <span>
              <span className="block text-xs font-semibold text-[var(--fg)]">
                DSP Buffett Indicator Analysis
              </span>
              <span className="mt-1 block text-[10px] leading-snug text-[var(--muted)]">
                Evaluate a company using DSP&apos;s Buffett-style investment
                analysis framework.
              </span>
            </span>
            <span className="ml-2 shrink-0 text-[var(--c-cashflow)]" aria-hidden>
              →
            </span>
          </Link>
        </div>
      ) : null}

      <nav
        className="flex min-h-0 flex-1 flex-col overflow-y-auto px-2.5 py-2.5"
        aria-label="Primary navigation"
      >
        <div className="flex flex-col gap-0.5">
          {nav.primary.map((item) => (
            <NavLink
              key={item.id}
              item={item}
              collapsed={collapsed}
              mobile={mobile}
              onNavigate={onNavigate}
              iconOnly={item.id === "research"}
            />
          ))}
        </div>
        {nav.research.length > 0 && !(collapsed && !mobile) ? (
          <div className="mt-3">
            <p className="section-label mb-1 px-2.5">Research</p>
            {nav.research.map((item) => (
              <NavLink
                key={item.id}
                item={item}
                collapsed={collapsed}
                mobile={mobile}
                onNavigate={onNavigate}
                exact={item.id === "research-hub"}
                dot
              />
            ))}
          </div>
        ) : null}
        {nav.more.length > 0 && !(collapsed && !mobile) ? (
          <div className="mt-3">
            <p className="section-label mb-1 px-2.5">More</p>
            {nav.more.map((item) => (
              <NavLink
                key={item.id}
                item={item}
                collapsed={collapsed}
                mobile={mobile}
                onNavigate={onNavigate}
              />
            ))}
          </div>
        ) : null}
      </nav>

      <div className="border-t border-[var(--border)] px-2.5 py-2">
        {nav.account.map((item) => (
          <NavLink
            key={item.id}
            item={item}
            collapsed={collapsed}
            mobile={mobile}
            onNavigate={onNavigate}
          />
        ))}
      </div>

      <div className="border-t border-[var(--border)] px-3 py-3">
        {collapsed && !mobile ? (
          <Link
            href={session && user ? "/profile" : "/login"}
            onClick={onNavigate}
            aria-label={session && user ? "Financial Profile" : "Sign in"}
            className="mx-auto flex h-11 w-11 items-center justify-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            <span
              aria-hidden
              className="flex h-7 w-7 items-center justify-center rounded-full bg-[linear-gradient(135deg,#7c6af7_0%,#2dd4bf_100%)] font-mono text-[11px] font-semibold text-white"
            >
              {(user?.displayName || "U").slice(0, 1).toUpperCase()}
            </span>
          </Link>
        ) : session && user ? (
          <div className="flex items-center gap-2.5">
            <Link
              href="/profile"
              onClick={onNavigate}
              aria-label="My Profile"
              className="flex min-w-0 flex-1 items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              <span
                aria-hidden
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[linear-gradient(135deg,#7c6af7_0%,#2dd4bf_100%)] font-mono text-[11px] font-semibold text-white"
              >
                {(user.displayName || "U").slice(0, 1).toUpperCase()}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-xs text-[var(--fg)]">{user.displayName}</span>
                <span className="block truncate font-mono text-[10px] text-[var(--muted)]">
                  {user.roles?.[0]?.replaceAll("_", " ") || "Signed in"}
                </span>
              </span>
            </Link>
            <Link
              href="/logout"
              onClick={onNavigate}
              aria-label="Log out"
              title="Log out"
              className="inline-flex min-h-11 items-center px-1 text-xs text-[var(--muted)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              <span aria-hidden>↩</span>
            </Link>
          </div>
        ) : (
          <Link
            href="/login"
            onClick={onNavigate}
            className="flex min-h-11 items-center justify-center rounded-[10px] border border-[var(--border)] text-xs text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            Sign in
          </Link>
        )}
      </div>
    </aside>
  );
}

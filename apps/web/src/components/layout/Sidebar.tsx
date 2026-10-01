"use client";

import {
  LayoutDashboard,
  Building2,
  Briefcase,
  BookOpen,
  ChevronDown,
  ChevronRight,
  Shield,
  FileText,
  Settings,
  User,
  Plus,
  ArrowRight,
  LogOut,
  GitCompareArrows,
  Sparkles,
  Ticket,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo, useState, type KeyboardEvent } from "react";

import {
  Sidebar as DsSidebar,
  SidebarGroup,
} from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import {
  filterShellNav,
  groupShellNav,
  isActivePath,
  type ShellNavIconId,
  type ShellNavItem,
} from "@/lib/shell";
import { cn } from "@/lib/utils";

const ICONS: Record<ShellNavIconId, LucideIcon> = {
  dashboard: LayoutDashboard,
  analysis: Building2,
  portfolio: Briefcase,
  research: BookOpen,
  reports: FileText,
  admin: Shield,
  settings: Settings,
  profile: User,
  compare: GitCompareArrows,
  copilot: Sparkles,
};

function NavLink({
  item,
  collapsed,
  mobile,
  onNavigate,
  nested = false,
}: {
  item: ShellNavItem;
  collapsed: boolean;
  mobile: boolean;
  onNavigate?: () => void;
  nested?: boolean;
}) {
  const pathname = usePathname();
  const active = isActivePath(pathname, item.href);
  const Icon = ICONS[item.icon];
  const hideLabel = collapsed && !mobile;

  return (
    <Link
      href={item.href}
      title={item.label}
      data-testid={`sidebar-${mobile ? "mobile" : "desktop"}-${item.id}`}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex min-h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-[13px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] motion-reduce:transition-none",
        hideLabel ? "justify-center" : "justify-start",
        nested && !hideLabel ? "pl-8" : null,
        active
          ? "bg-[var(--surface-2)] text-[var(--fg)]"
          : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
      )}
    >
      <Icon className="size-4 shrink-0" aria-hidden />
      {!hideLabel ? <span className="truncate">{item.label}</span> : null}
      {hideLabel ? <span className="sr-only">{item.label}</span> : null}
    </Link>
  );
}

function NavTree({
  items,
  collapsed,
  mobile,
  onNavigate,
}: {
  items: ShellNavItem[];
  collapsed: boolean;
  mobile: boolean;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  return (
    <>
      {items.map((item) => {
        const hasChildren = Boolean(item.children?.length);
        const childActive = item.children?.some((c) =>
          isActivePath(pathname, c.href),
        );
        const open =
          expanded[item.id] ?? (childActive || isActivePath(pathname, item.href));

        return (
          <div key={item.id} className="flex flex-col gap-0.5">
            <div className="flex items-center gap-0.5">
              <div className="min-w-0 flex-1">
                <NavLink
                  item={item}
                  collapsed={collapsed}
                  mobile={mobile}
                  onNavigate={onNavigate}
                />
              </div>
              {hasChildren && !(collapsed && !mobile) ? (
                <button
                  type="button"
                  className="inline-flex size-11 shrink-0 items-center justify-center rounded-[var(--radius-md)] text-[var(--muted)] hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                  data-testid={`sidebar-${mobile ? "mobile" : "desktop"}-${item.id}-expand`}
                  aria-expanded={open}
                  aria-label={
                    open
                      ? `Collapse ${item.label} submenu`
                      : `Expand ${item.label} submenu`
                  }
                  onClick={() =>
                    setExpanded((s) => ({ ...s, [item.id]: !open }))
                  }
                >
                  {open ? (
                    <ChevronDown className="size-4" aria-hidden />
                  ) : (
                    <ChevronRight className="size-4" aria-hidden />
                  )}
                </button>
              ) : null}
            </div>
            {hasChildren && open && !(collapsed && !mobile)
              ? item.children!.map((child) => (
                  <NavLink
                    key={child.id}
                    item={child}
                    collapsed={collapsed}
                    mobile={mobile}
                    onNavigate={onNavigate}
                    nested
                  />
                ))
              : null}
          </div>
        );
      })}
    </>
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

  const groups = useMemo(() => {
    const filtered = filterShellNav(permissions, roles);
    return groupShellNav(filtered);
  }, [permissions, roles]);

  const recentSearches = useDashboardPrefsStore((s) => s.recentSearches);
  const primaryItems: ShellNavItem[] = [
    { id: "dashboard", href: "/dashboard", label: "Dashboard", icon: "dashboard", section: "overview", description: "Your research overview" },
    { id: "companies", href: "/companies", label: "Companies", icon: "analysis", section: "research", description: "Company directory" },
    { id: "compare", href: "/compare", label: "Compare", icon: "compare", section: "research", description: "Compare companies" },
    { id: "portfolio", href: "/portfolio", label: "Portfolio", icon: "portfolio", section: "research", description: "Your portfolio" },
    { id: "copilot", href: "/copilot", label: "AI Copilot", icon: "copilot", section: "research", description: "Evidence-backed explanations" },
    { id: "advisor", href: "/advisor", label: "Advisor", icon: "profile", section: "research", description: "Advisor workspace" },
  ];
  const researchItems: ShellNavItem[] = [
    { id: "research-hub", href: "/research", label: "Research Hub", icon: "research", section: "research", description: "Saved research" },
    { id: "institutional", href: "/research/institutional", label: "Institutional", icon: "reports", section: "research", description: "Institutional reports" },
    { id: "canvas", href: "/research/canvas", label: "Canvas", icon: "research", section: "research", description: "Research notebook" },
    { id: "intelligence", href: "/research/intelligence", label: "Intelligence", icon: "research", section: "research", description: "Research insights" },
  ];
  // Keep permission-filtered legacy tools discoverable without duplicating the main links.
  const mainPaths = new Set([...primaryItems, ...researchItems].map((item) => item.href));
  const moreItems = groups.flatMap((group) => group.items).flatMap((item) => {
    const children = item.children?.filter((child) => !mainPaths.has(child.href));
    if (mainPaths.has(item.href)) return children ? [...children] : [];
    if (["/analysis", "/profile", "/settings"].includes(item.href)) return children ? [...children] : [];
    return [{ ...item, children }];
  });

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
      data-testid={mobile ? "mobile-sidebar" : "desktop-sidebar"}
      className={cn(
        "shrink-0 transition-[width] duration-200 motion-reduce:transition-none",
        mobile
          ? "flex h-full w-[220px] flex-col"
          : cn(
              "sticky top-0 hidden h-dvh flex-col overflow-y-auto border-r border-[var(--border)] bg-[var(--surface)] md:flex",
              collapsed ? "w-[4.5rem]" : "w-[220px]",
            ),
      )}
      aria-label="Primary"
      data-collapsed={collapsed && !mobile ? "true" : undefined}
    >
      <Link href="/" onClick={onNavigate} data-testid={`sidebar-${mobile ? "mobile" : "desktop"}-home`} className="border-b border-[var(--border)] px-[18px] pb-4 pt-5">
        <span className="flex items-center gap-2.5"><span className="size-[26px] shrink-0 rounded-full bg-[linear-gradient(135deg,#7c6af7,#2dd4bf)]" /><span className="font-[family-name:var(--font-display)] text-lg">{!(collapsed && !mobile) && "DSP"}</span></span>
        {!(collapsed && !mobile) && <span className="mt-1 block font-mono text-[10px] tracking-wider text-[var(--muted)]">AI RESEARCH</span>}
      </Link>
      <div className="border-b border-[var(--border)] p-3">
        <Link href="/analysis" onClick={onNavigate} data-testid={`sidebar-${mobile ? "mobile" : "desktop"}-new-research`} title="Start New Research" className="flex min-h-10 items-center justify-center gap-2 rounded-[10px] border border-[var(--border)] bg-[var(--surface-2)] px-2 text-[13px] transition-colors hover:border-[var(--accent)]">
          <Plus className="size-4 shrink-0" />{!(collapsed && !mobile) && "Start New Research"}
        </Link>
      </div>
      {!(collapsed && !mobile) && <div className="space-y-3 px-3.5 pb-2 pt-3">
        <div>
          <p className="mb-1 font-mono text-[10px] tracking-wider text-[var(--muted)]">RECENT SEARCHES</p>
          {recentSearches.length ? recentSearches.slice(0, 3).map(({ query }) => <Link key={query} href={`/analysis?symbol=${encodeURIComponent(query)}`} onClick={onNavigate} data-testid={`sidebar-${mobile ? "mobile" : "desktop"}-recent-${query}`} className="block truncate rounded-lg px-2 py-1.5 text-xs text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]">{query}</Link>) : <p data-testid={`sidebar-${mobile ? "mobile" : "desktop"}-empty-history`} className="py-2 text-xs text-[var(--muted)]">Your searches will appear here</p>}
        </div>
        <Link href="/analysis?intent=dsp_indicator" onClick={onNavigate} data-testid={`sidebar-${mobile ? "mobile" : "desktop"}-buffett`} className="flex items-center gap-2 rounded-xl border border-[var(--c-cashflow)]/30 bg-[var(--c-cashflow)]/10 p-3">
          <span><span className="block text-xs font-semibold">DSP Buffett Indicator Analysis</span><span className="mt-1 block text-[10px] leading-relaxed text-[var(--muted)]">Evaluate a company using DSP&apos;s Buffett-style investment analysis framework.</span></span><ArrowRight className="size-4 shrink-0 text-[var(--c-cashflow)]" />
        </Link>
      </div>}

      <DsSidebar
        collapsed={collapsed && !mobile}
        className="!w-full flex-1 border-0 bg-transparent"
        onKeyDown={onNavKeyDown}
      >
        <SidebarGroup
          label="Primary"
          collapsed={collapsed && !mobile}
        >
          <NavTree
            items={primaryItems}
            collapsed={collapsed}
            mobile={mobile}
            onNavigate={onNavigate}
          />
        </SidebarGroup>

        <SidebarGroup label="Research" collapsed={collapsed && !mobile}>
          <NavTree items={researchItems} collapsed={collapsed} mobile={mobile} onNavigate={onNavigate} />
        </SidebarGroup>
        {moreItems.length > 0 && (
          <SidebarGroup
            label="More"
            collapsed={collapsed && !mobile}
          >
            <NavTree
              items={moreItems}
              collapsed={collapsed}
              mobile={mobile}
              onNavigate={onNavigate}
            />
          </SidebarGroup>
        )}
      </DsSidebar>
      <div className="mt-auto space-y-1 border-t border-[var(--border)] p-2.5">
        {[
          { href: "/profile", label: "Financial Profile", icon: User },
          { href: "/pricing", label: "Pricing", icon: Ticket },
          { href: "/settings", label: "Settings", icon: Settings },
        ].map(({ href, label, icon: Icon }) => <Link key={href} href={href} title={label} onClick={onNavigate} data-testid={`sidebar-${mobile ? "mobile" : "desktop"}-account-${label.toLowerCase().replaceAll(" ", "-")}`} className="flex min-h-9 items-center gap-2.5 rounded-lg px-2.5 text-xs text-[var(--muted)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"><Icon className="size-4 shrink-0" />{!(collapsed && !mobile) && label}</Link>)}
        <div className="flex items-center justify-between gap-2 border-t border-[var(--border)] px-2 pt-3">
          <Link href={session ? "/profile" : "/login"} onClick={onNavigate} data-testid={`sidebar-${mobile ? "mobile" : "desktop"}-account`} className="flex min-h-9 min-w-0 items-center gap-2 text-xs">
            <span className="grid size-7 shrink-0 place-items-center rounded-full border border-[var(--border)] bg-[var(--accent-soft)] text-[var(--accent)]">{user ? user.displayName.slice(0, 2).toUpperCase() : <User className="size-4" />}</span>
            {!(collapsed && !mobile) && <span className="truncate">{user?.displayName || "Log in"}</span>}
          </Link>
          {session && !(collapsed && !mobile) && <Link href="/logout" onClick={onNavigate} data-testid={`sidebar-${mobile ? "mobile" : "desktop"}-logout`} aria-label="Log out" className="p-2 text-[var(--muted)] hover:text-[var(--fg)]"><LogOut className="size-4" /></Link>}
        </div>
      </div>
    </aside>
  );
}

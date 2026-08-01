"use client";

import {
  LayoutDashboard,
  Building2,
  Briefcase,
  BookOpen,
  ChevronDown,
  ChevronRight,
  Shield,
  Settings,
  User,
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
import { env } from "@/lib/env";
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
  admin: Shield,
  settings: Settings,
  profile: User,
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
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={cn(
        "inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-md)] px-2.5 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] motion-reduce:transition-none",
        hideLabel ? "justify-center" : "justify-start",
        nested && !hideLabel ? "pl-8" : null,
        active
          ? "bg-[var(--accent-soft)] text-[var(--accent)]"
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
              "hidden md:flex md:flex-col md:border-r md:border-[var(--border)] md:bg-[var(--surface)]",
              collapsed ? "md:w-[4.5rem]" : "md:w-60",
            ),
      )}
      aria-label="Primary"
      data-collapsed={collapsed && !mobile ? "true" : undefined}
    >
      <div
        className={cn(
          "border-b border-[var(--border)] px-3 py-4",
          collapsed && !mobile ? "px-2 text-center" : "",
        )}
      >
        <Link
          href="/dashboard"
          onClick={onNavigate}
          className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          <p
            className={cn(
              "font-[family-name:var(--font-display)] tracking-tight text-[var(--accent)]",
              collapsed && !mobile ? "text-sm" : "text-lg",
            )}
          >
            {collapsed && !mobile ? "DSP" : env.appName}
          </p>
          {!(collapsed && !mobile) ? (
            <p className="mt-0.5 text-xs text-[var(--muted)]">{env.tagline}</p>
          ) : null}
        </Link>
      </div>

      <DsSidebar
        collapsed={collapsed && !mobile}
        className="!w-full flex-1 border-0 bg-transparent"
        onKeyDown={onNavKeyDown}
      >
        {groups.map((group) => (
          <SidebarGroup
            key={group.section}
            label={group.label}
            collapsed={collapsed && !mobile}
          >
            <NavTree
              items={group.items}
              collapsed={collapsed}
              mobile={mobile}
              onNavigate={onNavigate}
            />
          </SidebarGroup>
        ))}
      </DsSidebar>
    </aside>
  );
}

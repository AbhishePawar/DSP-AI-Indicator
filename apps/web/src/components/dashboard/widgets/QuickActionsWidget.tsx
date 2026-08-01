"use client";

import Link from "next/link";

import { Button } from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";
import { canAccessNavItem, SHELL_NAV } from "@/lib/shell";
import { DashboardWidgetShell } from "../DashboardWidgetShell";

/** RC3-003 — Reinforce research journey: Analysis → Research → Portfolio → Reports. */
const ACTIONS = [
  {
    href: "/analysis",
    label: "1 · Company Analysis",
    id: "analysis",
    hint: "Flagship research",
  },
  {
    href: "/research",
    label: "2 · Research Workspace",
    id: "research",
    hint: "Library & history",
  },
  {
    href: "/portfolio",
    label: "3 · Portfolio",
    id: "portfolio",
    hint: "Coverage review",
  },
  {
    href: "/research/institutional",
    label: "4 · Research Reports",
    id: "research",
    hint: "Publish & export",
  },
  { href: "/settings", label: "Settings", id: "settings", hint: "Preferences" },
  { href: "/profile", label: "Profile", id: "profile", hint: "Identity" },
  {
    href: "/admin",
    label: "Administration",
    id: "admin",
    hint: "Ops",
  },
] as const;

export function QuickActionsWidget() {
  const { session, user } = useAuth();
  const permissions = session?.permissions ?? user?.permissions ?? [];
  const roles = session?.roles ?? user?.roles ?? [];

  const visible = ACTIONS.filter((action) => {
    if (action.href === "/research/institutional") {
      const research = SHELL_NAV.find((n) => n.id === "research");
      const child = research?.children?.find(
        (c) => c.id === "research-institutional",
      );
      if (!research || !canAccessNavItem(research, permissions, roles)) {
        return false;
      }
      return child
        ? canAccessNavItem(child, permissions, roles)
        : true;
    }
    const nav = SHELL_NAV.find((n) => n.id === action.id);
    if (!nav) return true;
    return canAccessNavItem(nav, permissions, roles);
  });

  return (
    <DashboardWidgetShell
      title="Research journey"
      description="Primary institutional workflow — Analysis → Research → Portfolio → Reports"
      span={2}
    >
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {visible.map((action) => (
          <Link key={`${action.href}-${action.label}`} href={action.href}>
            <Button variant="secondary" className="w-full justify-start">
              <span className="flex flex-col items-start gap-0.5 text-left">
                <span>{action.label}</span>
                <span className="text-[10px] font-normal text-[var(--muted)]">
                  {action.hint}
                </span>
              </span>
            </Button>
          </Link>
        ))}
      </div>
    </DashboardWidgetShell>
  );
}

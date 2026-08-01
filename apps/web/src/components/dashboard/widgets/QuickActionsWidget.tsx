"use client";

import Link from "next/link";

import { Button } from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";
import { canAccessNavItem, SHELL_NAV } from "@/lib/shell";
import { DashboardWidgetShell } from "../DashboardWidgetShell";

const ACTIONS = [
  { href: "/analysis", label: "Analyze Company", id: "analysis" },
  { href: "/research", label: "Open Research Workspace", id: "research" },
  { href: "/portfolio", label: "Open Portfolio", id: "portfolio" },
  { href: "/reports", label: "Recent Reports", id: "reports" },
  { href: "/copilot", label: "AI Copilot", id: "copilot" },
  { href: "/admin", label: "Administration", id: "admin" },
  { href: "/settings", label: "Settings", id: "settings" },
  { href: "/profile", label: "Profile", id: "profile" },
] as const;

export function QuickActionsWidget() {
  const { session, user } = useAuth();
  const permissions = session?.permissions ?? user?.permissions ?? [];
  const roles = session?.roles ?? user?.roles ?? [];

  const visible = ACTIONS.filter((action) => {
    const nav = SHELL_NAV.find((n) => n.id === action.id);
    if (!nav) return true;
    return canAccessNavItem(nav, permissions, roles);
  });

  return (
    <DashboardWidgetShell
      title="Quick Actions"
      description="Jump to primary workspaces"
      span={2}
    >
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {visible.map((action) => (
          <Link key={action.href} href={action.href}>
            <Button variant="secondary" className="w-full justify-start">
              {action.label}
            </Button>
          </Link>
        ))}
      </div>
    </DashboardWidgetShell>
  );
}

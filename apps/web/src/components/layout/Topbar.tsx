"use client";

/**
 * EPIC-F003 — Sticky application header with reference ZIP Diagnostics action.
 */

import { ChevronLeft, ChevronRight, Search, Menu, Activity } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import {
  Avatar,
  AvatarFallback,
  Button,
  Header,
  UserMenu,
} from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";

import { env } from "@/lib/env";
import { useUiStore } from "@/lib/shell";

export function Topbar({
  onMenuClick,
  onToggleCollapse,
  sidebarCollapsed,
}: {
  onMenuClick: () => void;
  onToggleCollapse: () => void;
  sidebarCollapsed: boolean;
}) {
  const { user, session } = useAuth();
  const router = useRouter();
  const setCommandPaletteOpen = useUiStore((s) => s.setCommandPaletteOpen);
  const initials = (user?.displayName || "U").slice(0, 2).toUpperCase();

  return (
    <Header
      aria-label="Application header"
      data-testid="app-topbar"
      className="!h-12 !min-h-11 !gap-2 !border-b !border-[var(--border)] !bg-[var(--card)] !px-4 !py-0 motion-reduce:transition-none sm:!min-h-12"
      left={
        <div className="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              data-testid="open-navigation"
              className="size-9 min-h-11 px-0 md:hidden"
              onClick={onMenuClick}
              aria-label="Open navigation menu"
            >
              <Menu className="size-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="hidden size-9 px-0 md:inline-flex"
              data-testid="toggle-sidebar"
              onClick={onToggleCollapse}
              aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              aria-pressed={sidebarCollapsed}
            >
              {sidebarCollapsed ? (
                <ChevronRight data-icon="inline-start" aria-hidden />
              ) : (
                <ChevronLeft data-icon="inline-start" aria-hidden />
              )}
            </Button>
            <Link
              href="/dashboard"
              data-testid="topbar-home"
              className="flex shrink-0 items-center gap-2 font-[family-name:var(--font-heading)] text-[15px] font-medium tracking-tight text-[var(--foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              aria-label={`${env.appName} home`}
            >
              <span className="size-5 shrink-0 rounded-full bg-[linear-gradient(135deg,#7c6af7,#2dd4bf)]" />
              <span className="tracking-tight">DSP</span>
            </Link>
          </div>
        </div>
      }
      right={
        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
          <Button
            variant="ghost"
            size="sm"
            data-testid="open-command-palette"
            className="size-9 px-0 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            onClick={() => setCommandPaletteOpen(true)}
            aria-label="Open search and command palette"
          >
            <Search className="size-4" aria-hidden />
          </Button>
          <Link
            href="/diagnostics"
            data-testid="topbar-diagnostics"
            className="hidden items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)]/50 px-3 py-1 font-mono text-xs text-[var(--muted-foreground)] transition-colors hover:border-[var(--accent)] hover:text-[var(--foreground)] sm:inline-flex"
            title="System & Runtime Diagnostics"
          >
            <Activity className="size-3.5" aria-hidden />
            <span>Diagnostics</span>
          </Link>
          {session && user ? (
            <UserMenu
              name={user.displayName}
              email={user.email || undefined}
              avatar={
                <Avatar className="size-7 border border-[var(--border)]">
                  <AvatarFallback className="bg-[linear-gradient(135deg,#7c6af7,#2dd4bf)] font-mono text-[10px] font-bold text-white">
                    {initials}
                  </AvatarFallback>
                </Avatar>
              }
              items={[
                {
                  id: "profile",
                  label: "Profile",
                  onSelect: () => router.push("/profile"),
                },
                {
                  id: "settings",
                  label: "Settings",
                  onSelect: () => router.push("/settings"),
                },
                {
                  id: "diagnostics",
                  label: "Diagnostics",
                  onSelect: () => router.push("/diagnostics"),
                },
                {
                  id: "logout",
                  label: "Logout",
                  destructive: true,
                  onSelect: () => {
                    router.push("/logout");
                  },
                },
              ]}
            />
          ) : (
            <Link
              href="/login"
              data-testid="topbar-login"
              className="rounded-lg border border-[var(--border)] px-3.5 py-1.5 font-[family-name:var(--font-body)] text-[13px] font-medium text-[var(--muted-foreground)] transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)]"
            >
              Log in
            </Link>
          )}
        </div>
      }
    />
  );
}

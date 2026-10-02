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
      className="!h-12 !min-h-12 !gap-2 !px-4 !py-0 motion-reduce:transition-none"
      left={
        <div className="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              data-testid="open-navigation"
              className="size-9 px-0 md:hidden"
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
              className="flex shrink-0 items-center gap-2 font-[family-name:var(--font-display)] text-[15px] tracking-tight text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              aria-label={`${env.appName} home`}
            >
              <span className="size-5 rounded-full bg-[linear-gradient(135deg,#7c6af7,#2dd4bf)]" /> DSP
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
            className="size-9 px-0"
            onClick={() => setCommandPaletteOpen(true)}
            aria-label="Open search and command palette"
          >
            <Search className="size-4" aria-hidden />
          </Button>
          <Link
            href="/diagnostics"
            data-testid="topbar-diagnostics"
            className="hidden items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted)] transition-colors hover:border-[var(--accent)] hover:text-[var(--fg)] sm:inline-flex"
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
                <Avatar className="size-7">
                  <AvatarFallback className="text-[10px]">{initials}</AvatarFallback>
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
            <Link href="/login" data-testid="topbar-login" className="rounded-lg border border-[var(--border)] px-3.5 py-1.5 text-[13px] text-[var(--muted)] transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)]">Log in</Link>
          )}
        </div>
      }
    />
  );
}

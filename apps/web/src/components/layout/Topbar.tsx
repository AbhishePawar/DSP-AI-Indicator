"use client";

/**
 * EPIC-F003 — Sticky application header.
 */

import { Bell, Search } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import {
  Avatar,
  AvatarFallback,
  Badge,
  Button,
  Header,
  Input,
  ThemeSwitcher,
  UserMenu,
} from "@/components/ds";
import { LegalNavLinks } from "@/components/legal/LegalNavLinks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { sessionStatusLabel } from "@/lib/auth/types";
import { env } from "@/lib/env";
import { useUiStore } from "@/lib/shell";
import { Breadcrumbs } from "./Breadcrumbs";

export function Topbar({
  onMenuClick,
  onToggleCollapse,
  sidebarCollapsed,
}: {
  onMenuClick: () => void;
  onToggleCollapse: () => void;
  sidebarCollapsed: boolean;
}) {
  const { user, session, status } = useAuth();
  const router = useRouter();
  const setCommandPaletteOpen = useUiStore((s) => s.setCommandPaletteOpen);
  const initials = (user?.displayName || "U").slice(0, 2).toUpperCase();
  const envLabel =
    env.environment === "production"
      ? "PROD"
      : env.environment === "test"
        ? "TEST"
        : "DEV";

  return (
    <Header
      aria-label="Application header"
      className="h-auto min-h-14 py-2 motion-reduce:transition-none"
      left={
        <div className="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="md:hidden"
              onClick={onMenuClick}
              aria-label="Open navigation menu"
            >
              Menu
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="hidden md:inline-flex"
              onClick={onToggleCollapse}
              aria-label={
                sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"
              }
              aria-pressed={sidebarCollapsed}
            >
              {sidebarCollapsed ? "Expand" : "Collapse"}
            </Button>
            <Link
              href="/dashboard"
              className="hidden shrink-0 font-[family-name:var(--font-display)] text-sm tracking-tight text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] lg:inline"
              aria-label={`${env.appName} home`}
            >
              DSP
            </Link>
          </div>
          <div className="min-w-0">
            <Breadcrumbs />
          </div>
        </div>
      }
      center={
        <button
          type="button"
          onClick={() => setCommandPaletteOpen(true)}
          className="flex min-h-11 w-full max-w-md items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-left text-sm text-[var(--muted)] transition hover:border-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] motion-reduce:transition-none"
          aria-label="Open search and command palette"
        >
          <Search className="size-4 shrink-0" aria-hidden />
          <span className="flex-1 truncate">Search pages…</span>
          <kbd className="hidden rounded border border-[var(--border)] px-1.5 py-0.5 font-mono text-[10px] sm:inline">
            Ctrl+K
          </kbd>
        </button>
      }
      right={
        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="md:hidden"
            onClick={() => setCommandPaletteOpen(true)}
            aria-label="Open search and command palette"
          >
            <Search className="size-4" aria-hidden />
          </Button>
          <div className="relative hidden w-40 xl:block">
            <Input
              readOnly
              placeholder="Search…"
              aria-label="Global search (opens command palette)"
              className="h-8 cursor-pointer text-xs"
              onFocus={() => setCommandPaletteOpen(true)}
              onClick={() => setCommandPaletteOpen(true)}
            />
          </div>
          <Button
            variant="ghost"
            size="sm"
            aria-label="Notifications (coming soon)"
            title="Notifications — UI only"
            disabled
            className="relative"
          >
            <Bell className="size-4" aria-hidden />
          </Button>
          <LegalNavLinks
            density="header"
            className="hidden max-w-[16rem] lg:flex"
          />
          <Badge variant="accent" className="hidden font-mono text-[10px] sm:inline-flex">
            v{env.foundationVersion}
          </Badge>
          <Badge
            variant="outline"
            className="hidden font-mono text-[10px] md:inline-flex"
            aria-label={`Environment ${envLabel}`}
          >
            {envLabel}
          </Badge>
          {session && user ? (
            <span className="hidden text-xs text-[var(--muted)] 2xl:inline">
              {sessionStatusLabel(status)}
            </span>
          ) : null}
          <ThemeSwitcher />
          {session && user ? (
            <UserMenu
              name={user.displayName}
              email={user.email || undefined}
              avatar={
                <Avatar className="size-7">
                  <AvatarFallback className="text-[10px]">
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
                  id: "sessions",
                  label: "Sessions",
                  onSelect: () => router.push("/profile"),
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
            <Link href="/login">
              <Button size="sm" variant="secondary">
                Sign in
              </Button>
            </Link>
          )}
        </div>
      }
    />
  );
}

"use client";

/**
 * Application header — Figma Make TopBar: title row, diagnostics, identity.
 * Auth, command palette, and theme remain production controls.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";

import {
  Avatar,
  AvatarFallback,
  Button,
  ThemeSwitcher,
  UserMenu,
} from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";
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
  const { user, session } = useAuth();
  const router = useRouter();
  const setCommandPaletteOpen = useUiStore((s) => s.setCommandPaletteOpen);
  const initials = (user?.displayName || "U").slice(0, 2).toUpperCase();

  return (
    <header
      aria-label="Application header"
      className="page-header"
    >
      <div className="flex min-w-0 items-center gap-2">
        <Button
          variant="ghost"
          className="min-h-11 md:hidden"
          onClick={onMenuClick}
          aria-label="Open navigation menu"
        >
          Menu
        </Button>
        <Button
          variant="ghost"
          className="hidden min-h-11 md:inline-flex"
          onClick={onToggleCollapse}
          aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-pressed={sidebarCollapsed}
        >
          {sidebarCollapsed ? "Expand" : "Collapse"}
        </Button>
        {/* Breadcrumb trail collides with header controls below 640px; the Menu drawer carries navigation there. */}
        <div className="hidden min-w-0 sm:block">
          <Breadcrumbs />
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          className="min-h-11"
          onClick={() => setCommandPaletteOpen(true)}
          aria-label="Open command palette"
        >
          Commands
        </Button>
        <Link
          href="/diagnostics"
          className="hidden rounded-lg border border-[var(--border)] px-3.5 py-1.5 text-xs text-[var(--muted)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] sm:inline-flex"
        >
          Diagnostics
        </Link>
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
                label: "Financial Profile",
                onSelect: () => router.push("/profile"),
              },
              {
                id: "settings",
                label: "Settings",
                onSelect: () => router.push("/settings"),
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
    </header>
  );
}

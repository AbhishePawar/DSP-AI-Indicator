"use client";

/**
 * Application header — ordinary clients get brand + account only.
 * Operator/admin keep breadcrumbs and diagnostic chrome.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";

import {
  Avatar,
  AvatarFallback,
  Badge,
  Button,
  Header,
  ThemeSwitcher,
  UserMenu,
} from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";
import { sessionStatusLabel } from "@/lib/auth/types";
import { env } from "@/lib/env";
import { resolveShellAudience } from "@/lib/shell";
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
  const permissions = session?.permissions ?? user?.permissions ?? [];
  const roles = session?.roles ?? user?.roles ?? [];
  const audience = resolveShellAudience(permissions, roles);
  const ordinary = audience === "ordinary";
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
      className="h-14 py-0 motion-reduce:transition-none"
      left={
        <div className="flex min-w-0 items-center gap-2">
          <Button
            variant="ghost"
            className="min-h-11 md:hidden"
            onClick={onMenuClick}
            aria-label="Open navigation menu"
          >
            Menu
          </Button>
          {!ordinary ? (
            <Button
              variant="ghost"
              className="hidden min-h-11 md:inline-flex"
              onClick={onToggleCollapse}
              aria-label={
                sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"
              }
              aria-pressed={sidebarCollapsed}
            >
              {sidebarCollapsed ? "Expand" : "Collapse"}
            </Button>
          ) : null}
          <Link
            href="/dashboard"
            className="shrink-0 font-[family-name:var(--font-display)] text-sm tracking-tight text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] sm:text-base"
            aria-label={`${env.appName} home`}
          >
            {env.appName}
          </Link>
          {!ordinary ? (
            <div className="hidden min-w-0 lg:block">
              <Breadcrumbs />
            </div>
          ) : null}
        </div>
      }
      right={
        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
          {!ordinary ? (
            <>
              <Badge
                variant="accent"
                className="hidden font-mono text-[10px] sm:inline-flex"
              >
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
            </>
          ) : null}
          <ThemeSwitcher compact />
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

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Dropdown, DropdownItem } from "@/components/ui/Dropdown";
import { useAuth } from "@/lib/auth/AuthProvider";
import { sessionStatusLabel } from "@/lib/auth/types";
import { env } from "@/lib/env";
import { useTheme, type ThemeMode } from "@/providers/ThemeProvider";
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
  const { user, session, status, logout } = useAuth();
  const { mode, setMode } = useTheme();
  const router = useRouter();

  return (
    <header className="sticky top-0 z-30 border-b border-[var(--border)] bg-[var(--surface)]/90 backdrop-blur-md">
      <div className="flex items-center justify-between gap-3 px-3 py-3 sm:px-4">
        <div className="flex min-w-0 items-center gap-2">
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
            aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-pressed={sidebarCollapsed}
          >
            {sidebarCollapsed ? "Expand" : "Collapse"}
          </Button>
          <div className="min-w-0">
            <Breadcrumbs />
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="hidden font-mono text-[10px] text-[var(--muted)] lg:inline">
            v{env.frontendVersion} · {env.environment}
          </span>
          {session && user ? (
            <span className="hidden text-xs text-[var(--muted)] lg:inline">
              {user.displayName} · {user.role} · {sessionStatusLabel(status)}
            </span>
          ) : (
            <span className="hidden text-xs text-[var(--muted)] lg:inline">
              Guest · {sessionStatusLabel(status)}
            </span>
          )}
          <label className="sr-only" htmlFor="theme-select">
            Theme
          </label>
          <select
            id="theme-select"
            value={mode}
            onChange={(e) => setMode(e.target.value as ThemeMode)}
            className="rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            aria-label="Color theme"
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">System</option>
          </select>
          {session ? (
            <Dropdown label="Account">
              <DropdownItem onClick={() => router.push("/profile")}>
                Profile
              </DropdownItem>
              <DropdownItem
                onClick={() => {
                  logout();
                  router.push("/login");
                }}
              >
                Logout
              </DropdownItem>
            </Dropdown>
          ) : (
            <Link href="/login">
              <Button size="sm" variant="secondary">
                Sign in
              </Button>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}

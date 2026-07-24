"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Dropdown, DropdownItem } from "@/components/ui/Dropdown";
import { useAuth } from "@/lib/auth/AuthProvider";
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
  const { session, logout } = useAuth();
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
          <span className="hidden text-xs text-[var(--muted)] lg:inline">
            {session?.username || session?.subject} · {session?.role}
          </span>
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
          <Dropdown label="Account">
            <DropdownItem
              onClick={() => {
                logout();
                router.push("/login");
              }}
            >
              Logout
            </DropdownItem>
          </Dropdown>
        </div>
      </div>
    </header>
  );
}

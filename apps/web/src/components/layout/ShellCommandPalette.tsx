"use client";

/**
 * EPIC-F003 — Command palette (Ctrl+K).
 * RC3-003 — RBAC-filtered like the sidebar; unfinished AUX routes hidden.
 */

import { useRouter } from "next/navigation";
import { useMemo } from "react";

import { CommandPalette, type CommandPaletteItem } from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";
import { filterResearchQuickActions } from "@/lib/research-canvas";
import { searchableRoutes, useUiStore } from "@/lib/shell";

function isAllowedPath(
  path: string,
  allowed: ReadonlySet<string>,
): boolean {
  if (allowed.has(path)) return true;
  // Favourites/recents may be nested under allowed shells (e.g. /research/…).
  for (const base of allowed) {
    if (path === base || path.startsWith(`${base}/`)) return true;
  }
  if (path.startsWith("/docs") || path.startsWith("/documentation")) {
    return true;
  }
  return false;
}

export function ShellCommandPalette() {
  const router = useRouter();
  const { session, user } = useAuth();
  const permissions = session?.permissions ?? user?.permissions ?? [];
  const roles = session?.roles ?? user?.roles ?? [];
  const open = useUiStore((s) => s.commandPaletteOpen);
  const setOpen = useUiStore((s) => s.setCommandPaletteOpen);
  const recentPages = useUiStore((s) => s.recentPages);
  const favouritePages = useUiStore((s) => s.favouritePages);
  const toggleFavourite = useUiStore((s) => s.toggleFavourite);

  const items = useMemo(() => {
    const list: CommandPaletteItem[] = [];
    const routes = searchableRoutes(permissions, roles);
    const allowed = new Set(routes.map((r) => r.path));
    // Always allow shell roots that filterShellNav exposed (incl. dashboard via nav).
    allowed.add("/dashboard");

    for (const fav of favouritePages) {
      if (!isAllowedPath(fav.path, allowed)) continue;
      list.push({
        id: `fav-${fav.path}`,
        label: fav.title,
        keywords: `${fav.path} favourite`,
        group: "Favourites",
        onSelect: () => router.push(fav.path),
      });
    }

    for (const recent of recentPages) {
      if (!isAllowedPath(recent.path, allowed)) continue;
      list.push({
        id: `recent-${recent.path}`,
        label: recent.title,
        keywords: `${recent.path} recent`,
        group: "Recent",
        onSelect: () => router.push(recent.path),
      });
    }

    for (const route of routes) {
      list.push({
        id: `route-${route.id}`,
        label: route.title,
        keywords: `${route.path} ${route.keywords ?? ""} ${route.description ?? ""}`,
        group: route.group ?? "Navigation",
        onSelect: () => router.push(route.path),
      });
    }

    // EPIC-014/015 — Research OS quick actions (RBAC + feature-flag filtered)
    for (const action of filterResearchQuickActions(permissions, roles)) {
      list.push({
        id: action.id,
        label: action.label,
        keywords: action.keywords,
        group: "Quick Actions",
        onSelect: () => router.push(action.href),
      });
    }

    list.push({
      id: "action-toggle-favourite",
      label: "Toggle favourite for current page",
      keywords: "favourite star bookmark",
      group: "Actions",
      onSelect: () => {
        if (typeof window === "undefined") return;
        const path = window.location.pathname;
        const title =
          document.title.replace(/\s*[·|].*$/, "").trim() || path;
        toggleFavourite(path, title);
      },
    });

    return list;
  }, [
    favouritePages,
    permissions,
    recentPages,
    roles,
    router,
    toggleFavourite,
  ]);

  return (
    <CommandPalette
      open={open}
      onOpenChange={setOpen}
      items={items}
      enableShortcut
      placeholder="Search pages and navigate…"
      emptyMessage="No matching routes."
      title="Quick navigation"
    />
  );
}

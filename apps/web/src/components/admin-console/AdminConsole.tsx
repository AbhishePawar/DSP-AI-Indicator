"use client";

/**
 * EPIC-F008 — Enterprise Administration Console.
 * Consumes A010 /api/v1/admin/* only. Display backend outputs — no client admin logic.
 */

import { useCallback, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";

import { Button, EmptyState } from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  ADMIN_ACCESS_PERMISSIONS,
  ADMIN_SECTIONS,
  isAdminSectionId,
  useAdminConsolePrefsStore,
} from "@/lib/admin-console";
import { useCollapsePanelsBelowLg } from "@/lib/a11y";
import { cn } from "@/lib/utils";
import { AdminLeftNav } from "./LeftNav";
import { AdminRightPanel } from "./RightPanel";
import {
  AuditSection,
  BetaSection,
  ExportSection,
  IdentitySection,
  MetricsSection,
  OverviewSection,
  PlatformSection,
  ResearchRefsSection,
  WorkflowSection,
} from "./Sections";

function hasAdminAccess(permissions: string[], roles: string[]): boolean {
  if (roles.includes("administrator")) return true;
  return ADMIN_ACCESS_PERMISSIONS.some((p) => permissions.includes(p));
}

function Toolbar({
  leftOpen,
  rightOpen,
  onToggleLeft,
  onToggleRight,
  onRefresh,
  refreshing,
}: {
  leftOpen: boolean;
  rightOpen: boolean;
  onToggleLeft: () => void;
  onToggleRight: () => void;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  return (
    <div className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] bg-[var(--surface)]/95 px-3 py-2 backdrop-blur motion-reduce:backdrop-blur-none">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant="ghost"
          onClick={onToggleLeft}
          aria-pressed={leftOpen}
          aria-label={leftOpen ? "Hide navigation panel" : "Show navigation panel"}
        >
          {leftOpen ? "Hide nav" : "Show nav"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={onToggleRight}
          aria-pressed={rightOpen}
          aria-label={rightOpen ? "Hide context panel" : "Show context panel"}
        >
          {rightOpen ? "Hide context" : "Show context"}
        </Button>
        <span className="hidden text-xs text-[var(--muted)] md:inline">
          Shortcuts: 1–9 sections · [ / ] panels · Ctrl+Enter refresh
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={onRefresh} disabled={refreshing}>
          {refreshing ? "Refreshing…" : "Refresh"}
        </Button>
      </div>
    </div>
  );
}

export function AdminConsole() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { session, user, status } = useAuth();
  const token = session?.accessToken;

  const activeSection = useAdminConsolePrefsStore((s) => s.activeSection);
  const setActiveSection = useAdminConsolePrefsStore((s) => s.setActiveSection);
  const leftOpen = useAdminConsolePrefsStore((s) => s.leftOpen);
  const rightOpen = useAdminConsolePrefsStore((s) => s.rightOpen);
  const toggleLeft = useAdminConsolePrefsStore((s) => s.toggleLeft);
  const toggleRight = useAdminConsolePrefsStore((s) => s.toggleRight);
  const setLeftOpen = useAdminConsolePrefsStore((s) => s.setLeftOpen);
  const setRightOpen = useAdminConsolePrefsStore((s) => s.setRightOpen);
  const selectedUserId = useAdminConsolePrefsStore((s) => s.selectedUserId);
  const selectedRoleId = useAdminConsolePrefsStore((s) => s.selectedRoleId);
  const setSelectedUserId = useAdminConsolePrefsStore(
    (s) => s.setSelectedUserId,
  );
  const setSelectedRoleId = useAdminConsolePrefsStore(
    (s) => s.setSelectedRoleId,
  );

  useCollapsePanelsBelowLg(setLeftOpen, setRightOpen);

  useEffect(() => {
    const section = searchParams.get("section");
    const userId = searchParams.get("user");
    const roleId = searchParams.get("role");
    if (section && isAdminSectionId(section)) {
      setActiveSection(section);
    }
    if (userId) setSelectedUserId(userId);
    if (roleId) setSelectedRoleId(roleId);
  }, [
    searchParams,
    setActiveSection,
    setSelectedUserId,
    setSelectedRoleId,
  ]);

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("section", activeSection);
    if (selectedUserId) params.set("user", selectedUserId);
    if (selectedRoleId) params.set("role", selectedRoleId);
    const next = params.toString();
    const current = new URLSearchParams(searchParams.toString());
    const currentNormalized = new URLSearchParams();
    const curSection = current.get("section");
    const curUser = current.get("user");
    const curRole = current.get("role");
    if (curSection) currentNormalized.set("section", curSection);
    if (curUser) currentNormalized.set("user", curUser);
    if (curRole) currentNormalized.set("role", curRole);
    if (next !== currentNormalized.toString()) {
      router.replace(`/admin?${next}`, { scroll: false });
    }
  }, [activeSection, selectedUserId, selectedRoleId, router, searchParams]);

  const refresh = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ["admin"] });
  }, [queryClient]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || target?.isContentEditable) {
        return;
      }
      if (e.key === "[" ) {
        e.preventDefault();
        toggleLeft();
      } else if (e.key === "]") {
        e.preventDefault();
        toggleRight();
      } else if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        refresh();
      } else if (/^[1-8]$/.test(e.key)) {
        const section = ADMIN_SECTIONS.find((s) => s.shortcut === e.key);
        if (section) {
          e.preventDefault();
          setActiveSection(section.id);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [refresh, setActiveSection, toggleLeft, toggleRight]);

  if (status === "loading") {
    return (
      <EmptyState
        title="Loading session…"
        description="Checking administration access."
      />
    );
  }

  const permissions = user?.permissions || session?.permissions || [];
  const roles = user?.roles || session?.roles || [];
  if (!session || !hasAdminAccess(permissions, roles)) {
    return (
      <EmptyState
        title="Access unavailable."
        description="Administration requires manage_users, manage_roles, configure_platform, view_audit, or the administrator role."
        action={
          <Button size="sm" variant="secondary" onClick={() => router.push("/dashboard")}>
            Return to dashboard
          </Button>
        }
      />
    );
  }

  const resourceKey =
    selectedUserId || selectedRoleId || `section:${activeSection}`;

  const refreshing = false;

  return (
    <div className="flex min-h-[70vh] flex-col rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--bg)]">
      <Toolbar
        leftOpen={leftOpen}
        rightOpen={rightOpen}
        onToggleLeft={toggleLeft}
        onToggleRight={toggleRight}
        onRefresh={refresh}
        refreshing={refreshing}
      />
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <aside
          aria-label="Administration navigation"
          className={cn(
            "border-[var(--border)] bg-[var(--surface)] lg:w-72 lg:shrink-0 lg:border-r",
            leftOpen ? "block" : "hidden",
          )}
        >
          <AdminLeftNav onRefresh={refresh} refreshing={refreshing} />
        </aside>
        <div
          role="region"
          aria-label="Main administration view"
          className="min-w-0 flex-1 overflow-auto p-4"
        >
          {activeSection === "overview" ? (
            <OverviewSection token={token} />
          ) : null}
          {activeSection === "identity" ? (
            <IdentitySection token={token} />
          ) : null}
          {activeSection === "audit" ? <AuditSection token={token} /> : null}
          {activeSection === "platform" ? (
            <PlatformSection token={token} />
          ) : null}
          {activeSection === "metrics" ? (
            <MetricsSection token={token} />
          ) : null}
          {activeSection === "workflow" ? (
            <WorkflowSection token={token} />
          ) : null}
          {activeSection === "research" ? (
            <ResearchRefsSection token={token} />
          ) : null}
          {activeSection === "export" ? <ExportSection token={token} /> : null}
          {activeSection === "beta" ? <BetaSection token={token} /> : null}
        </div>
        <aside
          aria-label="Administration context panel"
          className={cn(
            "border-[var(--border)] bg-[var(--surface)] lg:w-72 lg:shrink-0 lg:border-l",
            rightOpen ? "block" : "hidden",
          )}
        >
          <AdminRightPanel resourceKey={resourceKey} />
        </aside>
      </div>
    </div>
  );
}

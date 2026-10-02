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
import { ZipAdminPanel } from "./ZipAdminPanel";
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

/**
 * Figma Make `AdminPanel.tsx` shell: TopBar (rendered by the route) → flat
 * scroll column of cards. Section switching uses Figma pill chips instead of
 * the retired three-panel workspace nav; A010 sections are unchanged.
 */
function SectionChips({
  activeSection,
  onSelect,
  rightOpen,
  onToggleRight,
  onRefresh,
  refreshing,
}: {
  activeSection: string;
  onSelect: (id: (typeof ADMIN_SECTIONS)[number]["id"]) => void;
  rightOpen: boolean;
  onToggleRight: () => void;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <nav aria-label="Administration sections" className="flex flex-wrap gap-2">
        {ADMIN_SECTIONS.map((section) => {
          const active = activeSection === section.id;
          return (
            <button
              key={section.id}
              type="button"
              aria-current={active ? "page" : undefined}
              title={`${section.description} (shortcut ${section.shortcut})`}
              onClick={() => onSelect(section.id)}
              className={cn(
                "min-h-11 rounded-[20px] border px-3 font-mono text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
                active
                  ? "border-[var(--border)] bg-[var(--surface-2)] text-[var(--fg)]"
                  : "border-[var(--border)] text-[var(--muted)] hover:text-[var(--fg)]",
              )}
            >
              {section.label}
            </button>
          );
        })}
      </nav>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="ghost"
          onClick={onToggleRight}
          aria-pressed={rightOpen}
          aria-label={rightOpen ? "Hide context panel" : "Show context panel"}
        >
          {rightOpen ? "Hide context" : "Show context"}
        </Button>
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
  const rightOpen = useAdminConsolePrefsStore((s) => s.rightOpen);
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
      if (e.key === "]") {
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
  }, [refresh, setActiveSection, toggleRight]);

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
        title="Access denied"
        description="Administration requires manage_users, manage_roles, configure_platform, view_audit, or the administrator role. The server enforces this on every admin request."
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
    <div className="flex min-h-[70vh] flex-col gap-5">
      <SectionChips
        activeSection={activeSection}
        onSelect={setActiveSection}
        rightOpen={rightOpen}
        onToggleRight={toggleRight}
        onRefresh={refresh}
        refreshing={refreshing}
      />
      <p className="sr-only">
        Keyboard shortcuts: 1–9 switch sections, ] toggles the context panel,
        Ctrl+Enter refreshes.
      </p>
      <ZipAdminPanel token={token} />
      <div className="flex min-h-0 flex-1 flex-col gap-5 lg:flex-row">
        <div
          role="region"
          aria-label="Main administration view"
          className="flex min-w-0 flex-1 flex-col gap-5"
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
            "rounded-[var(--card-radius)] border border-[var(--border)] bg-[var(--surface)] lg:w-60 lg:shrink-0",
            rightOpen ? "block" : "hidden",
          )}
        >
          <AdminRightPanel resourceKey={resourceKey} />
        </aside>
      </div>
    </div>
  );
}

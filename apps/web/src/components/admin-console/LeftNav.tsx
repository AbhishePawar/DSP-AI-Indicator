"use client";

import { Button } from "@/components/ds";
import {
  ADMIN_SECTIONS,
  useAdminConsolePrefsStore,
} from "@/lib/admin-console";
import { cn } from "@/lib/utils";

export function AdminLeftNav({
  onRefresh,
  refreshing,
}: {
  onRefresh: () => void;
  refreshing: boolean;
}) {
  const activeSection = useAdminConsolePrefsStore((s) => s.activeSection);
  const setActiveSection = useAdminConsolePrefsStore((s) => s.setActiveSection);
  const selectedUserId = useAdminConsolePrefsStore((s) => s.selectedUserId);
  const selectedRoleId = useAdminConsolePrefsStore((s) => s.selectedRoleId);

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-3">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Administration
        </p>
        <Button size="sm" onClick={onRefresh} disabled={refreshing}>
          {refreshing ? "Refreshing…" : "Refresh data"}
        </Button>
        <p className="mt-2 text-xs text-[var(--muted)]">
          Display-only A010 console. No client-side administration logic.
        </p>
      </div>

      <nav aria-label="Administration sections">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Sections
        </p>
        <ul className="space-y-0.5">
          {ADMIN_SECTIONS.map((section) => (
            <li key={section.id}>
              <button
                type="button"
                className={cn(
                  "flex w-full items-center justify-between rounded-[var(--radius-md)] px-2 py-1.5 text-left text-sm",
                  activeSection === section.id
                    ? "bg-[var(--surface-2)] font-medium text-[var(--fg)]"
                    : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
                )}
                aria-current={
                  activeSection === section.id ? "page" : undefined
                }
                onClick={() => setActiveSection(section.id)}
              >
                <span>{section.label}</span>
                <span className="text-[10px] text-[var(--muted)]">
                  {section.shortcut}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Selection
        </p>
        <dl className="space-y-1 text-xs">
          <div className="flex justify-between gap-2">
            <dt className="text-[var(--muted)]">User</dt>
            <dd className="font-mono">{selectedUserId || "Data unavailable."}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt className="text-[var(--muted)]">Role</dt>
            <dd className="font-mono">{selectedRoleId || "Data unavailable."}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}

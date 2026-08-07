"use client";

import type { WorkspaceDashboard, WorkspaceNote } from "./types";

export function WorkspaceDashboardPanel({
  dashboard,
  onOpenNote,
}: {
  dashboard: WorkspaceDashboard;
  onOpenNote: (note: WorkspaceNote) => void;
}) {
  const sections: Array<{
    title: string;
    items: Array<{ key: string; label: string; note?: WorkspaceNote }>;
  }> = [
    {
      title: "Recent notes",
      items: (dashboard.recent_notes || []).map((n) => ({
        key: n.note_id,
        label: n.title || n.note_id,
        note: n,
      })),
    },
    {
      title: "Pending reviews",
      items: (dashboard.pending_reviews || []).map((n) => ({
        key: `p-${n.note_id}`,
        label: `${n.title || n.note_id} · ${n.status}`,
        note: n,
      })),
    },
    {
      title: "Published reports",
      items: (dashboard.published_reports || []).map((n) => ({
        key: `pub-${n.note_id}`,
        label: n.title || n.note_id,
        note: n,
      })),
    },
    {
      title: "Recent companies",
      items: (dashboard.recent_companies || []).map((c) => ({
        key: `co-${c}`,
        label: c,
      })),
    },
    {
      title: "Tasks",
      items: (dashboard.tasks || []).map((t, i) => ({
        key: `task-${i}`,
        label: String(t.title || t.note_id || "Task"),
      })),
    },
    {
      title: "Recent Copilot conversations",
      items: (dashboard.recent_copilot_conversations || []).map((c, i) => ({
        key: `copilot-${i}`,
        label: String(
          c.title || c.conversation_id || "Copilot conversation",
        ),
      })),
    },
  ];

  return (
    <div
      className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3"
      data-testid="rw-dashboard-panel"
    >
      {sections.map((section) => (
        <section
          key={section.title}
          className="rounded-md border border-[var(--border)] p-3"
        >
          <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            {section.title}
          </h2>
          <ul className="space-y-1 text-sm">
            {section.items.length === 0 ? (
              <li className="text-xs text-[var(--muted)]">Data unavailable.</li>
            ) : (
              section.items.slice(0, 5).map((item) => (
                <li key={item.key}>
                  {item.note ? (
                    <button
                      type="button"
                      className="text-left hover:underline"
                      onClick={() => onOpenNote(item.note!)}
                    >
                      {item.label}
                    </button>
                  ) : (
                    <span>{item.label}</span>
                  )}
                </li>
              ))
            )}
          </ul>
        </section>
      ))}
    </div>
  );
}

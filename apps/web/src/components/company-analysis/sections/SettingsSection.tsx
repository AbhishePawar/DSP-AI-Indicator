"use client";

/**
 * Institutional Company Workspace — Settings tab.
 *
 * Reuses the existing workspace preferences store and theme switcher — no
 * new preferences infrastructure.
 */

import { Button } from "@/components/ds";
import { ThemeSwitcher } from "@/components/ds/theme/theme-switcher";
import { useWorkspacePrefsStore } from "@/lib/company-analysis";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { FieldRow, SectionCard } from "../WorkspacePrimitives";

export function SettingsSection({ view }: { view: ResearchView }) {
  const leftOpen = useWorkspacePrefsStore((s) => s.leftOpen);
  const rightOpen = useWorkspacePrefsStore((s) => s.rightOpen);
  const toggleLeft = useWorkspacePrefsStore((s) => s.toggleLeft);
  const toggleRight = useWorkspacePrefsStore((s) => s.toggleRight);
  const notes = useWorkspacePrefsStore((s) => s.notes);
  const tags = useWorkspacePrefsStore((s) => s.tags);
  const removeNote = useWorkspacePrefsStore((s) => s.removeNote);
  const removeTag = useWorkspacePrefsStore((s) => s.removeTag);

  return (
    <div className="space-y-4">
      <SectionCard
        title="Appearance"
        description="Theme preference — applies across the whole platform, not just this workspace."
      >
        <ThemeSwitcher />
      </SectionCard>

      <SectionCard title="Workspace layout">
        <dl>
          <FieldRow label="Left navigation" value={leftOpen ? "Shown" : "Hidden"} />
          <FieldRow label="Context panel" value={rightOpen ? "Shown" : "Hidden"} />
        </dl>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" onClick={toggleLeft}>
            {leftOpen ? "Hide" : "Show"} navigation
          </Button>
          <Button size="sm" variant="secondary" onClick={toggleRight}>
            {rightOpen ? "Hide" : "Show"} context panel
          </Button>
        </div>
      </SectionCard>

      <SectionCard
        title="Notes"
        description={`Analyst notes for ${view.ticker} — session-local, stored in this browser only.`}
      >
        {notes.filter((n) => n.symbol === view.ticker.toUpperCase()).length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {notes
              .filter((n) => n.symbol === view.ticker.toUpperCase())
              .map((n) => (
                <li key={n.id} className="flex items-start justify-between gap-3">
                  <span>{n.text}</span>
                  <Button size="sm" variant="ghost" onClick={() => removeNote(n.id)}>
                    Remove
                  </Button>
                </li>
              ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard
        title="Tags"
        description={`Tags for ${view.ticker} — session-local, stored in this browser only.`}
      >
        {tags.filter((t) => t.symbol === view.ticker.toUpperCase()).length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="flex flex-wrap gap-2 text-sm">
            {tags
              .filter((t) => t.symbol === view.ticker.toUpperCase())
              .map((t) => (
                <li
                  key={t.id}
                  className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] px-3 py-1"
                >
                  {t.label}
                  <button
                    type="button"
                    aria-label={`Remove tag ${t.label}`}
                    onClick={() => removeTag(t.id)}
                    className="text-[var(--muted)] hover:text-[var(--fg)]"
                  >
                    ×
                  </button>
                </li>
              ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}

"use client";

import { Button } from "@/components/ds";
import {
  SETTINGS_SECTIONS,
  useSettingsPrefsStore,
} from "@/lib/settings";
import { cn } from "@/lib/utils";

export function SettingsLeftNav() {
  const activeSection = useSettingsPrefsStore((s) => s.activeSection);
  const setActiveSection = useSettingsPrefsStore((s) => s.setActiveSection);
  const density = useSettingsPrefsStore((s) => s.density);
  const fontSize = useSettingsPrefsStore((s) => s.fontSize);

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-3">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Settings
        </p>
        <p className="text-xs text-[var(--muted)]">
          UI preferences persist locally. Account data uses existing auth APIs
          only.
        </p>
      </div>

      <nav aria-label="Settings sections">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Sections
        </p>
        <ul className="space-y-0.5">
          {SETTINGS_SECTIONS.map((section) => (
            <li key={section.id}>
              <button
                type="button"
                className={cn(
                  "flex w-full items-center justify-between rounded-[var(--radius-md)] px-2 py-1.5 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
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
          Appearance snapshot
        </p>
        <dl className="space-y-1 text-xs">
          <div className="flex justify-between gap-2">
            <dt className="text-[var(--muted)]">Density</dt>
            <dd>{density}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt className="text-[var(--muted)]">Font</dt>
            <dd>{fontSize}</dd>
          </div>
        </dl>
        <Button
          size="sm"
          variant="ghost"
          className="mt-2"
          onClick={() => setActiveSection("appearance")}
        >
          Edit appearance
        </Button>
      </div>
    </div>
  );
}

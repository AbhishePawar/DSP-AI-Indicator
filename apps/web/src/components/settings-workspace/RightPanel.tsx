"use client";

import Link from "next/link";
import { useState } from "react";

import { Button, Input } from "@/components/ds";
import {
  SETTINGS_SECTIONS,
  useSettingsPrefsStore,
} from "@/lib/settings";

export function SettingsRightPanel() {
  const notes = useSettingsPrefsStore((s) => s.notes);
  const addNote = useSettingsPrefsStore((s) => s.addNote);
  const removeNote = useSettingsPrefsStore((s) => s.removeNote);
  const setActiveSection = useSettingsPrefsStore((s) => s.setActiveSection);
  const [noteText, setNoteText] = useState("");

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-3">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Notes
        </p>
        <form
          className="space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            addNote(noteText);
            setNoteText("");
          }}
        >
          <Input
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="Local note"
            aria-label="Add settings note"
          />
          <Button size="sm" type="submit" variant="secondary">
            Add note
          </Button>
        </form>
        {notes.length === 0 ? (
          <p className="mt-2 text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {notes.map((n) => (
              <li
                key={n.id}
                className="rounded-[var(--radius-md)] border border-[var(--border)] p-2 text-xs"
              >
                <p>{n.text}</p>
                <button
                  type="button"
                  className="mt-1 text-[var(--accent)] hover:underline"
                  onClick={() => removeNote(n.id)}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Related resources
        </p>
        <ul className="space-y-1 text-sm">
          <li>
            <Link className="text-[var(--accent)] hover:underline" href="/profile">
              Full profile page
            </Link>
          </li>
          <li>
            <Link
              className="text-[var(--accent)] hover:underline"
              href="/diagnostics"
            >
              Diagnostics
            </Link>
          </li>
          <li>
            <Link className="text-[var(--accent)] hover:underline" href="/docs">
              Documentation
            </Link>
          </li>
        </ul>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Quick actions
        </p>
        <div className="flex flex-col gap-1">
          {SETTINGS_SECTIONS.slice(0, 4).map((section) => (
            <Button
              key={section.id}
              size="sm"
              variant="ghost"
              className="justify-start"
              onClick={() => setActiveSection(section.id)}
            >
              {section.label}
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
}

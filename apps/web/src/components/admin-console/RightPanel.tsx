"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Button, Input } from "@/components/ds";
import {
  ADMIN_SECTIONS,
  useAdminConsolePrefsStore,
} from "@/lib/admin-console";

export function AdminRightPanel({
  resourceKey,
}: {
  resourceKey: string;
}) {
  const notes = useAdminConsolePrefsStore((s) => s.notes);
  const tags = useAdminConsolePrefsStore((s) => s.tags);
  const addNote = useAdminConsolePrefsStore((s) => s.addNote);
  const removeNote = useAdminConsolePrefsStore((s) => s.removeNote);
  const addTag = useAdminConsolePrefsStore((s) => s.addTag);
  const removeTag = useAdminConsolePrefsStore((s) => s.removeTag);
  const setActiveSection = useAdminConsolePrefsStore((s) => s.setActiveSection);
  const [noteText, setNoteText] = useState("");
  const [tagText, setTagText] = useState("");

  const key = resourceKey.trim() || "console";
  const scopedNotes = notes.filter((n) => n.resourceKey === key);
  const scopedTags = tags.filter((t) => t.resourceKey === key);

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
            addNote(key, noteText);
            setNoteText("");
          }}
        >
          <Input
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="Local note"
            aria-label="Add administration note"
          />
          <Button size="sm" type="submit" variant="secondary">
            Add note
          </Button>
        </form>
        {scopedNotes.length === 0 ? (
          <p className="mt-2 text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {scopedNotes.map((n) => (
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
          Tags
        </p>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            addTag(key, tagText);
            setTagText("");
          }}
        >
          <Input
            value={tagText}
            onChange={(e) => setTagText(e.target.value)}
            placeholder="Tag"
            aria-label="Add administration tag"
          />
          <Button size="sm" type="submit" variant="secondary">
            Add
          </Button>
        </form>
        <div className="mt-2 flex flex-wrap gap-1">
          {scopedTags.length === 0 ? (
            <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
          ) : (
            scopedTags.map((t) => (
              <Badge key={t.id} variant="outline">
                {t.label}{" "}
                <button
                  type="button"
                  className="ml-1"
                  aria-label={`Remove tag ${t.label}`}
                  onClick={() => removeTag(t.id)}
                >
                  ×
                </button>
              </Badge>
            ))
          )}
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Related resources
        </p>
        <ul className="space-y-1 text-sm">
          <li>
            <Link className="text-[var(--accent)] hover:underline" href="/profile">
              Profile & sessions
            </Link>
          </li>
          <li>
            <Link
              className="text-[var(--accent)] hover:underline"
              href="/docs/administrator-guide"
            >
              Administrator guide
            </Link>
          </li>
          <li>
            <Link className="text-[var(--accent)] hover:underline" href="/diagnostics">
              Diagnostics
            </Link>
          </li>
        </ul>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Quick actions
        </p>
        <div className="flex flex-col gap-1">
          {ADMIN_SECTIONS.slice(0, 4).map((section) => (
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
          <Button
            size="sm"
            variant="ghost"
            className="justify-start"
            onClick={() => setActiveSection("export")}
          >
            Export
          </Button>
        </div>
      </div>
    </div>
  );
}

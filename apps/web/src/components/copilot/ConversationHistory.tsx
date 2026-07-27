"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { CopilotConversation } from "@/lib/copilot/types";

export function ConversationHistory({
  conversations,
  activeId,
  onSelect,
  onNew,
}: {
  conversations: CopilotConversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}) {
  return (
    <Card>
      <CardHeader
        title="Conversation History"
        description="Session only"
        action={
          <button
            type="button"
            onClick={onNew}
            className="rounded-md border border-[var(--border)] px-2 py-1 text-xs hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            New
          </button>
        }
      />
      <CardBody>
        {conversations.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No conversations yet.</p>
        ) : (
          <ul className="space-y-1" aria-label="Conversation history">
            {conversations.map((conversation) => {
              const active = conversation.id === activeId;
              return (
                <li key={conversation.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(conversation.id)}
                    aria-current={active ? "true" : undefined}
                    className={`w-full rounded-md px-2.5 py-2 text-left text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                      active
                        ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                        : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
                    }`}
                  >
                    <span className="line-clamp-2">{conversation.title}</span>
                    <span className="mt-0.5 block font-mono text-[10px] opacity-80">
                      {new Date(conversation.updatedAt).toLocaleString()}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}

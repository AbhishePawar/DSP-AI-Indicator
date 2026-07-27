"use client";

import type { CopilotMessage } from "@/lib/copilot/types";
import { ResearchCitationList } from "./ResearchCitationList";

export function MessageBubble({
  message,
  ticker,
}: {
  message: CopilotMessage;
  ticker?: string | null;
}) {
  const isUser = message.role === "user";
  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
      data-role={message.role}
    >
      <div
        className={`max-w-[90%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
          isUser
            ? "bg-[var(--accent)] text-[var(--accent-fg)]"
            : "border border-[var(--border)] bg-[var(--surface-2)] text-[var(--fg)]"
        }`}
      >
        <p className="text-[10px] uppercase tracking-wider opacity-70">
          {isUser ? "You" : "Copilot"}
        </p>
        <p className="mt-1">{message.content}</p>
        {!isUser ? (
          <ResearchCitationList
            citations={message.citations}
            ticker={ticker}
          />
        ) : null}
      </div>
    </div>
  );
}

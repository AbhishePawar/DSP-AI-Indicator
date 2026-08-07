"use client";

import type { CopilotMessage } from "@/lib/copilot/types";
import { ResearchCitationList } from "./ResearchCitationList";

function renderMarkdownLite(content: string) {
  const blocks = content.split("\n");
  return blocks.map((line, index) => {
    if (line.startsWith("## ")) {
      return (
        <h3 key={index} className="mt-2 text-sm font-semibold">
          {line.slice(3)}
        </h3>
      );
    }
    if (line.startsWith("# ")) {
      return (
        <h2 key={index} className="mt-2 text-base font-semibold">
          {line.slice(2)}
        </h2>
      );
    }
    if (line.startsWith("|") && line.endsWith("|")) {
      return (
        <pre
          key={index}
          className="mt-1 overflow-x-auto rounded bg-[var(--surface-1)] px-2 py-1 text-[11px]"
        >
          {line}
        </pre>
      );
    }
    if (!line.trim()) {
      return <div key={index} className="h-2" />;
    }
    return (
      <p key={index} className="mt-0.5">
        {line}
      </p>
    );
  });
}

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
        className={`max-w-[90%] rounded-lg px-3 py-2 text-sm ${
          isUser
            ? "bg-[var(--accent)] text-[var(--accent-fg)] whitespace-pre-wrap"
            : "border border-[var(--border)] bg-[var(--surface-2)] text-[var(--fg)]"
        }`}
      >
        <p className="text-[10px] uppercase tracking-wider opacity-70">
          {isUser ? "You" : "Copilot"}
        </p>
        <div className="mt-1">
          {message.markdown && !isUser
            ? renderMarkdownLite(message.content)
            : <p className="whitespace-pre-wrap">{message.content}</p>}
        </div>
        {!isUser ? (
          <>
            <ResearchCitationList
              citations={message.citations}
              ticker={ticker}
            />
            {message.sources?.length ? (
              <div
                className="mt-2 border-t border-[var(--border)] pt-2"
                data-testid="copilot-sources"
              >
                <p className="text-[10px] uppercase tracking-wider text-[var(--muted)]">
                  Source references
                </p>
                <ul className="mt-1 space-y-0.5 text-[11px] text-[var(--muted)]">
                  {message.sources.map((source, index) => (
                    <li key={`${source.engine}-${index}`}>
                      {source.engine}
                      {source.detail ? ` · ${source.detail}` : ""}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}

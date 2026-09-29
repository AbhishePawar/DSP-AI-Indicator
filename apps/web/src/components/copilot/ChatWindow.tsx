"use client";

import { FormEvent, useEffect, useRef } from "react";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import type { CopilotMessage } from "@/lib/copilot/types";
import { MessageBubble } from "./MessageBubble";

export function ChatWindow({
  messages,
  typing,
  draft,
  onDraftChange,
  onSend,
  disabled,
  ticker,
}: {
  messages: CopilotMessage[];
  typing: boolean;
  draft: string;
  onDraftChange: (value: string) => void;
  onSend: (text: string) => void;
  disabled?: boolean;
  ticker?: string | null;
}) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, typing]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || disabled || typing) return;
    onSend(text);
  }

  return (
    <Card className="flex min-h-[28rem] flex-col">
      <CardHeader title="Chat" description="Copilot 2.0 — orchestrates engines; never invents numbers" />
      <CardBody className="flex flex-1 flex-col gap-3">
        <div
          className="max-h-[22rem] flex-1 space-y-3 overflow-y-auto pr-1"
          aria-live="polite"
          aria-label="Copilot messages"
        >
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              ticker={ticker}
            />
          ))}
          {typing ? (
            <div className="flex gap-3" role="status">
              <span
                aria-hidden
                className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full bg-[linear-gradient(135deg,#7c6af7,#2dd4bf)] font-mono text-[11px] text-white"
              >
                D
              </span>
              <div className="rounded-[4px_16px_16px_16px] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-[13px] text-[var(--muted)]">
                Copilot is preparing an answer…
              </div>
            </div>
          ) : null}
          <div ref={endRef} />
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 focus-within:border-[color-mix(in_srgb,var(--accent)_50%,transparent)]"
        >
          <Input
            value={draft}
            onChange={(e) => onDraftChange(e.target.value)}
            placeholder="Ask DSP Copilot about valuation, moat, risks…"
            aria-label="Copilot message"
            disabled={disabled || typing}
            className="border-0 bg-transparent shadow-none focus-visible:ring-0"
          />
          <Button
            type="submit"
            size="sm"
            disabled={disabled || typing || !draft.trim()}
            className="min-h-11 shrink-0"
          >
            Send
          </Button>
        </form>
      </CardBody>
    </Card>
  );
}

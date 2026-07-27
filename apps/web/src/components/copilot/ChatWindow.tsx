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
      <CardHeader title="Chat" description="Explainability assistant — no LLM" />
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
            <div className="text-sm text-[var(--muted)]" role="status">
              Copilot is preparing an answer…
            </div>
          ) : null}
          <div ref={endRef} />
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={draft}
            onChange={(e) => onDraftChange(e.target.value)}
            placeholder="Ask about valuation, moat, risks…"
            aria-label="Copilot message"
            disabled={disabled || typing}
          />
          <Button type="submit" disabled={disabled || typing || !draft.trim()}>
            Send
          </Button>
        </form>
      </CardBody>
    </Card>
  );
}

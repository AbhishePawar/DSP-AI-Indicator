"use client";

import { memo } from "react";

import { TraceLink } from "@/components/analysis/TraceLink";
import { ConfidenceBadge } from "@/components/trust/ConfidenceBadge";
import { Badge } from "@/components/ui/Badge";
import type {
  CopilotAnswer,
  CopilotCitation,
  CopilotMessage,
} from "@/lib/analysis/sprint6Copilot";

export function ContextBadge({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <span className="inline-flex min-h-8 items-center gap-1 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2 text-xs">
      <span className="text-[var(--muted)]">{label}</span>
      <span className="font-medium">{value}</span>
    </span>
  );
}

export function ThinkingIndicator() {
  return (
    <div
      className="flex items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--muted)]"
      role="status"
      aria-live="polite"
    >
      <span
        className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--accent)] motion-reduce:animate-none"
        aria-hidden
      />
      Looking up DSP Research…
    </div>
  );
}

export function CopilotCitationLink({ citation }: { citation: CopilotCitation }) {
  return (
    <TraceLink href={citation.href}>
      {citation.label}
    </TraceLink>
  );
}

export function EvidenceCitation({ items }: { items: string[] }) {
  if (!items.length) {
    return <p className="text-sm text-[var(--muted)]">No evidence listed.</p>;
  }
  return (
    <ul className="list-disc space-y-1 pl-5 text-sm">
      {items.map((i) => (
        <li key={i}>{i}</li>
      ))}
    </ul>
  );
}

export function RelatedResearchCard({
  sections,
}: {
  sections: CopilotAnswer["relatedSections"];
}) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        Related sections
      </p>
      <div className="mt-1 flex flex-wrap gap-2">
        {sections.map((s) => (
          <TraceLink key={s.id} href={s.href}>
            {s.title}
          </TraceLink>
        ))}
      </div>
    </div>
  );
}

export function SuggestedQuestionCard({
  question,
  onAsk,
}: {
  question: string;
  onAsk: (q: string) => void;
}) {
  return (
    <button
      type="button"
      className="min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-left text-sm hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
      onClick={() => onAsk(question)}
    >
      {question}
    </button>
  );
}

export const ResponseCard = memo(function ResponseCard({
  answer,
  onFollowUp,
}: {
  answer: CopilotAnswer;
  onFollowUp: (q: string) => void;
}) {
  return (
    <article className="space-y-3 rounded-md border border-[var(--border)] bg-[var(--surface)] p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <ConfidenceBadge level={answer.confidence} />
        {answer.isUnavailable ? <Badge tone="warning">Unavailable</Badge> : null}
        <Badge tone="neutral">Not investment advice</Badge>
      </div>

      <section>
        <h3 className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Short answer
        </h3>
        <p className="mt-1 font-medium">{answer.shortAnswer}</p>
      </section>

      <section>
        <h3 className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Detailed explanation
        </h3>
        <p className="mt-1 text-[var(--muted)]">{answer.detailedExplanation}</p>
      </section>

      <section>
        <h3 className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Supporting evidence
        </h3>
        <div className="mt-1">
          <EvidenceCitation items={answer.supportingEvidence} />
        </div>
      </section>

      <section>
        <h3 className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Confidence
        </h3>
        <p className="mt-1">{answer.confidenceLabel}</p>
      </section>

      <section>
        <h3 className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Limitations
        </h3>
        <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
          {answer.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </section>

      <RelatedResearchCard sections={answer.relatedSections} />

      <section>
        <h3 className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Citations
        </h3>
        <div className="mt-1 flex flex-wrap gap-2">
          {answer.citations.map((c) => (
            <CopilotCitationLink key={c.id} citation={c} />
          ))}
        </div>
      </section>

      <p className="text-xs text-[var(--muted)]">
        Source: {answer.sourceNote}
        <br />
        Methodology: {answer.methodologyNote}
      </p>

      <section>
        <h3 className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Next suggested question
        </h3>
        <div className="mt-2">
          <SuggestedQuestionCard
            question={answer.nextSuggestedQuestion}
            onAsk={onFollowUp}
          />
        </div>
      </section>

      <section>
        <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Follow-ups
        </h3>
        <div className="space-y-2">
          {answer.followUps.slice(0, 5).map((q) => (
            <SuggestedQuestionCard key={q} question={q} onAsk={onFollowUp} />
          ))}
        </div>
      </section>
    </article>
  );
});

export function CopilotMessageView({
  message,
  onFollowUp,
}: {
  message: CopilotMessage;
  onFollowUp: (q: string) => void;
}) {
  if (message.role === "system") {
    return (
      <p className="rounded-md border border-dashed border-[var(--border)] px-3 py-2 text-xs text-[var(--muted)]">
        {message.text}
      </p>
    );
  }
  if (message.role === "user") {
    return (
      <div className="ml-6 rounded-md bg-[var(--accent-soft)]/50 px-3 py-2 text-sm">
        <p className="text-xs text-[var(--muted)]">You</p>
        <p>{message.text}</p>
      </div>
    );
  }
  return (
    <div className="mr-2 space-y-2">
      <p className="text-xs text-[var(--muted)]">Research Copilot</p>
      {message.answer ? (
        <ResponseCard answer={message.answer} onFollowUp={onFollowUp} />
      ) : (
        <p className="text-sm">{message.text}</p>
      )}
    </div>
  );
}

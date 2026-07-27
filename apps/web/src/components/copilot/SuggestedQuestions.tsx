"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { SuggestedQuestion } from "@/lib/copilot/types";

export function SuggestedQuestions({
  questions,
  onSelect,
  disabled,
}: {
  questions: readonly SuggestedQuestion[];
  onSelect: (question: SuggestedQuestion) => void;
  disabled?: boolean;
}) {
  return (
    <Card>
      <CardHeader
        title="Suggested Questions"
        description="Deterministic explainability prompts"
      />
      <CardBody>
        <ul className="space-y-2" aria-label="Suggested questions">
          {questions.map((question) => (
            <li key={question.id}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onSelect(question)}
                className="w-full rounded-md border border-[var(--border)] px-3 py-2 text-left text-sm transition hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {question.label}
              </button>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

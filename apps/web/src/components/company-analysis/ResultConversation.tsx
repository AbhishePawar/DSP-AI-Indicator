"use client";

/**
 * Conversational result-page workspace for /analysis.
 *
 * The initial research result and every follow-up question live in one
 * vertical conversation. Follow-ups call the existing `/copilot/complete`
 * engine (already used by AiCopilotSection) — no client-side templating and
 * no invented valuation methodology. When no live analysis is loaded, the
 * page shows either an explicit, dev-only example fixture (behind
 * `exampleMode`) or a clean "Research unavailable" state — never fabricated
 * production data.
 */

import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import { useMutation } from "@tanstack/react-query";
import { MoreHorizontal, Pencil, RefreshCw, Share2, ArrowUp } from "lucide-react";

import { api } from "@/lib/api/client";
import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import { ApiClientError } from "@/lib/api/types";
import type { SuggestedQuestionId } from "@/lib/copilot/types";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { EXAMPLE_RESEARCH_VIEW } from "./exampleResearchView";
import { ResearchResponse } from "./ResearchResponse";

type FollowUpTurn = {
  id: string;
  question: string;
  status: "loading" | "ready" | "error";
  content?: string;
  citations?: string[];
  limitations?: string[];
  unavailable?: boolean;
  errorMessage?: string;
};

const SUGGESTIONS: Array<{ label: string; questionId: SuggestedQuestionId | "freeform" }> = [
  { label: "Run DSP Buffett-style analysis", questionId: "buffett" },
  { label: "Explain the key risks", questionId: "explain_risk" },
  { label: "Show valuation assumptions", questionId: "explain_valuation" },
  { label: "What should I investigate next?", questionId: "freeform" },
];

function describeError(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401) {
      return "Sign in required to ask follow-up research questions.";
    }
    return error.message || `Research request failed (${error.status}).`;
  }
  if (error instanceof Error) return error.message;
  return "Research unavailable.";
}

export function ResultConversation({
  view,
  exampleMode = false,
  token,
  analyseRequest = null,
  analyseResponse = null,
  onShare,
  onRefresh,
}: {
  view: ResearchView | null;
  exampleMode?: boolean;
  token?: string;
  analyseRequest?: AnalyseRequest | null;
  analyseResponse?: AnalyseResponse | null;
  onShare: () => void;
  onRefresh: () => void;
}) {
  const activeView = view ?? (exampleMode ? EXAMPLE_RESEARCH_VIEW : null);
  const canAskBackend = Boolean(view && analyseResponse);

  const [followUps, setFollowUps] = useState<FollowUpTurn[]>([]);
  const [draft, setDraft] = useState("");
  const idRef = useRef(0);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // Start a fresh conversation whenever the underlying company changes.
  useEffect(() => {
    setFollowUps([]);
  }, [activeView?.ticker]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [followUps.length]);

  const askMutation = useMutation({
    mutationFn: async (args: {
      id: string;
      questionId: SuggestedQuestionId | "freeform";
      text: string;
    }) =>
      api.copilotComplete(
        {
          question_id: args.questionId,
          freeform: args.questionId === "freeform" ? args.text : undefined,
          request: analyseRequest,
          response: analyseResponse,
          market_context: view
            ? { ticker: view.ticker, company: view.company, exchange: view.exchange }
            : null,
        },
        { token },
      ),
    onSuccess: (data, args) => {
      setFollowUps((prev) =>
        prev.map((turn) =>
          turn.id === args.id
            ? {
                ...turn,
                status: "ready",
                content: data.content || "Research unavailable.",
                citations: data.citations,
                limitations: data.limitations,
                unavailable: data.unavailable,
              }
            : turn,
        ),
      );
    },
    onError: (err, args) => {
      setFollowUps((prev) =>
        prev.map((turn) =>
          turn.id === args.id
            ? { ...turn, status: "error", errorMessage: describeError(err) }
            : turn,
        ),
      );
    },
  });

  function submitQuestion(questionId: SuggestedQuestionId | "freeform", text: string) {
    const trimmed = text.trim();
    if (!trimmed || askMutation.isPending) return;
    idRef.current += 1;
    const id = `turn-${idRef.current}`;
    setFollowUps((prev) => [...prev, { id, question: trimmed, status: "loading" }]);
    setDraft("");

    if (!canAskBackend) {
      setFollowUps((prev) =>
        prev.map((turn) =>
          turn.id === id
            ? {
                ...turn,
                status: "error",
                errorMessage: exampleMode
                  ? "Example data mode — connect a live analysis to ask real follow-up questions."
                  : "Run an analysis first to ask follow-up questions.",
              }
            : turn,
        ),
      );
      return;
    }
    askMutation.mutate({ id, questionId, text: trimmed });
  }

  function retry(turn: FollowUpTurn) {
    setFollowUps((prev) => prev.filter((t) => t.id !== turn.id));
    submitQuestion("freeform", turn.question);
  }

  function onComposerKeyDown(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey) return;
    // Avoid submitting mid-IME composition (CJK input, Safari's keyCode 229).
    if (event.nativeEvent.isComposing || (event.nativeEvent as unknown as { keyCode?: number }).keyCode === 229) {
      return;
    }
    event.preventDefault();
    submitQuestion("freeform", draft);
  }

  const company = activeView?.company ?? "Data unavailable";
  const ticker = activeView?.ticker ?? "—";
  const requestLine = activeView
    ? `Give me a DSP Buffett-style analysis of ${company}.`
    : "Give me a DSP Buffett-style analysis.";

  return (
    <div className="flex min-h-screen flex-col overflow-hidden bg-[var(--surface)]">
      {exampleMode && !view ? (
        <div className="border-b border-amber-200 bg-amber-50 px-5 py-2 text-center text-xs font-medium text-amber-800">
          Example data shown for layout preview. Live analysis data will replace this automatically.
        </div>
      ) : null}
      <header className="flex items-center justify-between border-b border-[var(--border)] px-5 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="truncate text-base font-semibold text-[var(--ink)]">
              {company} ({ticker})
            </h1>
            <Pencil className="size-4 text-[var(--muted)]" aria-hidden="true" />
          </div>
          <p className="text-xs text-[var(--muted)]">
            DSP AI Research · Updated{" "}
            {activeView?.analysedAt
              ? new Date(activeView.analysedAt).toLocaleString()
              : "Data unavailable"}
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onShare}
            className="inline-flex items-center gap-2 rounded-lg bg-[var(--surface-2)] px-3 py-2 text-sm font-medium text-[var(--ink)] hover:bg-[var(--accent-soft)]"
          >
            <Share2 className="size-4" /> Share
          </button>
          <button
            type="button"
            aria-label="More options"
            className="rounded-lg p-2 text-[var(--muted)] hover:bg-[var(--surface-2)]"
          >
            <MoreHorizontal className="size-5" />
          </button>
        </div>
      </header>

      <main className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-8 lg:px-12">
        <div className="mx-auto w-full max-w-3xl space-y-5">
          <UserBubble text={requestLine} caption="Research request" />

          <AssistantBubble>
            {activeView ? (
              <>
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-3 text-xs">
                    <span className="font-semibold text-[var(--accent-strong)]">DSP AI</span>
                    <span className="text-[var(--muted)]">Research Mode</span>
                  </div>
                  <button
                    type="button"
                    onClick={onRefresh}
                    aria-label="Regenerate result"
                    className="rounded p-1.5 text-[var(--muted)] hover:bg-[var(--surface-2)]"
                  >
                    <RefreshCw className="size-4" />
                  </button>
                </div>
                <ResearchResponse view={activeView} />
              </>
            ) : (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                <p className="text-sm font-medium text-[var(--ink)]">Research unavailable</p>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  Run analysis to load backend research outputs for this symbol.
                </p>
              </div>
            )}
          </AssistantBubble>

          {followUps.map((turn) => (
            <div key={turn.id} className="space-y-3">
              <UserBubble text={turn.question} />
              <AssistantBubble>
                {turn.status === "loading" ? (
                  <p className="text-sm text-[var(--muted)]" role="status">
                    DSP AI is researching…
                  </p>
                ) : turn.status === "error" ? (
                  <div className="rounded-xl border border-red-200 bg-red-50 p-3">
                    <p className="text-sm text-red-700">{turn.errorMessage}</p>
                    {canAskBackend ? (
                      <button
                        type="button"
                        onClick={() => retry(turn)}
                        className="mt-2 text-xs font-medium text-red-700 hover:underline"
                      >
                        Retry
                      </button>
                    ) : null}
                  </div>
                ) : (
                  <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                    <p className="text-sm leading-6 text-[var(--ink)]">{turn.content}</p>
                    {turn.citations?.length ? (
                      <p className="mt-2 text-[11px] text-[var(--muted)]">
                        Citations: {turn.citations.join(", ")}
                      </p>
                    ) : null}
                    {turn.limitations?.length ? (
                      <p className="mt-1 text-[11px] text-[var(--muted)]">
                        {turn.limitations.join(" · ")}
                      </p>
                    ) : null}
                  </div>
                )}
              </AssistantBubble>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </main>

      <div className="mx-auto w-[calc(100%-2rem)] max-w-3xl space-y-2 pb-1">
        <div className="flex flex-wrap gap-2" aria-label="Suggested follow-up questions">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion.label}
              type="button"
              onClick={() => submitQuestion(suggestion.questionId, suggestion.label)}
              disabled={askMutation.isPending}
              className="rounded-full border border-[var(--border)] px-3 py-1.5 text-xs text-[var(--muted)] hover:border-[var(--accent)] hover:text-[var(--accent-strong)] disabled:opacity-50"
            >
              {suggestion.label}
            </button>
          ))}
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            submitQuestion("freeform", draft);
          }}
          className="flex items-end gap-3 rounded-3xl border border-[var(--border)] bg-[var(--surface)] px-4 py-2.5 shadow-[var(--shadow-sm)]"
        >
          <label htmlFor="research-composer" className="sr-only">
            Ask a follow-up question
          </label>
          <textarea
            id="research-composer"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onComposerKeyDown}
            placeholder={`Ask a follow-up question about ${ticker}...`}
            rows={1}
            className="min-w-0 flex-1 resize-none bg-transparent py-1.5 text-sm leading-6 outline-none placeholder:text-[var(--muted)]"
            aria-label="Ask a follow-up question"
          />
          <button
            type="submit"
            disabled={!draft.trim() || askMutation.isPending}
            aria-label="Send follow-up"
            className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[var(--accent)] text-white hover:opacity-90 disabled:opacity-40"
          >
            <ArrowUp className="size-4" />
          </button>
        </form>
      </div>
      <p className="pb-2 pt-1 text-center text-[10px] text-[var(--muted)]">
        DSP AI can make mistakes. Please verify important information.
      </p>
    </div>
  );
}

function UserBubble({ text, caption }: { text: string; caption?: string }) {
  return (
    <div className="flex items-start justify-end gap-3">
      <div className="min-w-0 max-w-[85%]">
        <div className="rounded-2xl bg-[var(--accent-soft)] px-4 py-2 text-sm text-[var(--ink)]">
          {text}
        </div>
        {caption ? (
          <p className="mt-1 text-right text-[11px] text-[var(--muted)]">{caption}</p>
        ) : null}
      </div>
    </div>
  );
}

function AssistantBubble({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[var(--accent)] text-sm font-semibold text-white">
        D
      </div>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

export default ResultConversation;

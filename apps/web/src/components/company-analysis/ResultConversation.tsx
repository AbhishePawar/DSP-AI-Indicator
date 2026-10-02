"use client";

/**
 * Institutional Conversational Research Result Workspace for /analysis.
 *
 * Preserves the analytical hierarchy:
 * 1. RESEARCH RESULT (authoritative deterministic research models)
 * 2. EVIDENCE & ANALYSIS (provenance, sources, audit metadata)
 * 3. RESEARCH COPILOT & FOLLOW-UP (structured institutional research assistant)
 * 4. CONVERSATION TURNS (Answer → Supporting Evidence → Sources → Audit & Limitations)
 *
 * Backend calls route to the live /copilot/complete engine.
 * No client-side templating or synthetic AI data.
 */

import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Share2,
  RefreshCw,
  ArrowUp,
  AlertCircle,
  HelpCircle,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { api } from "@/lib/api/client";
import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import { ApiClientError } from "@/lib/api/types";
import type { SuggestedQuestionId } from "@/lib/copilot/types";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { EXAMPLE_RESEARCH_VIEW } from "./exampleResearchView";
import { ResearchResponse } from "./ResearchResponse";

export type FollowUpTurn = {
  id: string;
  question: string;
  status: "loading" | "ready" | "error";
  content?: string;
  citations?: string[];
  limitations?: string[];
  unavailable?: boolean;
  errorMessage?: string;
  timestamp: string;
};

export const RESEARCH_SUGGESTIONS: Array<{
  label: string;
  questionId: SuggestedQuestionId | "freeform";
  description: string;
}> = [
  {
    label: "Explain the valuation",
    questionId: "explain_valuation",
    description: "DCF model and intrinsic value drivers",
  },
  {
    label: "Why is margin of safety low?",
    questionId: "explain_margin_of_safety",
    description: "Downside buffer and discount rationale",
  },
  {
    label: "Explain the key risks",
    questionId: "explain_risk",
    description: "Vulnerabilities and risk factors",
  },
  {
    label: "Run DSP Buffett-style analysis",
    questionId: "buffett",
    description: "Durable competitive moat evaluation",
  },
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

  // Clear conversation when company changes
  useEffect(() => {
    setFollowUps([]);
  }, [activeView?.ticker]);

  useEffect(() => {
    if (typeof bottomRef.current?.scrollIntoView === "function") {
      bottomRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
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
                content: data.content || "Research explanation unavailable.",
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
    const timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    setFollowUps((prev) => [
      ...prev,
      { id, question: trimmed, status: "loading", timestamp },
    ]);
    setDraft("");

    if (!canAskBackend) {
      setFollowUps((prev) =>
        prev.map((turn) =>
          turn.id === id
            ? {
                ...turn,
                status: "error",
                errorMessage: exampleMode
                  ? "Example data mode — connect a live analysis session to ask research follow-up questions."
                  : "Run an analysis first to enable research follow-up questions.",
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
    if (
      event.nativeEvent.isComposing ||
      (event.nativeEvent as unknown as { keyCode?: number }).keyCode === 229
    ) {
      return;
    }
    event.preventDefault();
    submitQuestion("freeform", draft);
  }

  const company = activeView?.company ?? "Data unavailable";
  const ticker = activeView?.ticker ?? "—";

  return (
    <div className="flex min-h-screen flex-col bg-[var(--surface)] text-[var(--fg)]">
      {exampleMode && !view ? (
        <div className="border-b border-amber-200 bg-amber-50 px-5 py-2 text-center text-xs font-medium text-amber-900">
          Example fixture active. Live analysis results will populate automatically when connected.
        </div>
      ) : null}

      {/* Terminal Header */}
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] bg-[var(--surface-2)] px-6 py-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="truncate text-lg font-bold text-[var(--ink)]">
              {company}
            </h1>
            <span className="font-mono text-xs text-[var(--muted)]">
              {ticker} · {activeView?.exchange || "NYSE/NASDAQ"}
            </span>
            <Badge tone="neutral">Institutional Research</Badge>
          </div>
          <p className="mt-0.5 text-xs text-[var(--muted)]">
            DSP Deterministic Pipeline · Updated:{" "}
            {activeView?.analysedAt
              ? new Date(activeView.analysedAt).toLocaleString()
              : "Data unavailable"}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {activeView?.ticker ? (
            <Link
              href={`/analysis/compare?symbols=${activeView.ticker}`}
              className="inline-flex min-h-[44px] items-center gap-1.5 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs font-medium text-[var(--fg)] hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              Compare Peer <ExternalLink className="size-3.5 text-[var(--muted)]" />
            </Link>
          ) : null}
          <button
            type="button"
            onClick={onShare}
            className="inline-flex min-h-[44px] items-center gap-1.5 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs font-medium text-[var(--fg)] hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            <Share2 className="size-3.5" /> Share
          </button>
          <button
            type="button"
            onClick={onRefresh}
            aria-label="Refresh analysis"
            className="inline-flex min-h-[44px] items-center gap-1.5 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs font-medium text-[var(--fg)] hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            <RefreshCw className="size-3.5" /> Refresh
          </button>
        </div>
      </header>

      {/* Main Workspace Body */}
      <main className="min-h-0 flex-1 overflow-y-auto px-4 py-8 sm:px-6 lg:px-12">
        <div className="mx-auto w-full max-w-4xl space-y-8">
          {/* Section 1: Research Result */}
          <section aria-labelledby="primary-research-heading" className="space-y-4">
            <h2 id="primary-research-heading" className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
              1. Authoritative Research Result
            </h2>
            {activeView ? (
              <ResearchResponse view={activeView} />
            ) : (
              <Card>
                <CardBody className="p-6">
                  <h3 className="text-base font-semibold text-[var(--ink)]">Research unavailable</h3>
                  <p className="mt-1 text-sm text-[var(--muted)]">
                    Run an analysis to execute deterministic valuation, economic moat, and investment committee models for this security.
                  </p>
                </CardBody>
              </Card>
            )}
          </section>

          {/* Section 2: Research Interaction / Copilot */}
          <section aria-labelledby="copilot-section-heading" className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border)] pt-8">
              <div>
                <h2 id="copilot-section-heading" className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                  2. Research Interaction &amp; Follow-up Copilot
                </h2>
                <p className="text-xs text-[var(--muted)]">
                  Contextual research assistant grounded in authoritative session findings
                </p>
              </div>

              {/* Context Awareness Badge */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex min-h-[32px] items-center gap-1.5 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface-2)] px-2.5 py-1 text-xs">
                  <span className="text-[var(--muted)]">Context:</span>
                  <span className="font-semibold text-[var(--fg)]">{ticker}</span>
                  <span className="text-[var(--muted)]">({company})</span>
                </span>
                <Badge tone="neutral">
                  AI Provider: Bounded (Deterministic Engine)
                </Badge>
              </div>
            </div>

            {/* Conversation History */}
            <div className="space-y-4" role="log" aria-live="polite" aria-label="Research Copilot Conversation">
              {followUps.length === 0 ? (
                <div className="rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] bg-[var(--surface-2)] p-6 text-center">
                  <HelpCircle className="mx-auto size-6 text-[var(--muted)]" aria-hidden="true" />
                  <h3 className="mt-2 text-sm font-semibold text-[var(--fg)]">
                    No follow-up questions yet
                  </h3>
                  <p className="mt-1 text-xs text-[var(--muted)]">
                    Ask questions below or select a suggested topic to explore valuation, risk factors, or Buffett methodology.
                  </p>
                </div>
              ) : (
                followUps.map((turn) => (
                  <article
                    key={turn.id}
                    className="space-y-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)]"
                  >
                    {/* User Question */}
                    <div className="flex items-start justify-between gap-3 border-b border-[var(--border)] pb-3">
                      <div>
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--accent)]">
                          Analyst Inquiry
                        </span>
                        <p className="mt-0.5 text-sm font-medium text-[var(--ink)]">
                          {turn.question}
                        </p>
                      </div>
                      <span className="text-[11px] text-[var(--muted)]">
                        {turn.timestamp}
                      </span>
                    </div>

                    {/* Assistant Response State */}
                    {turn.status === "loading" ? (
                      <div className="flex items-center gap-3 py-3 text-sm text-[var(--muted)]" role="status">
                        <span
                          className="h-2.5 w-2.5 animate-pulse rounded-full bg-[var(--accent)] motion-reduce:animate-none"
                          aria-hidden="true"
                        />
                        <span>Analyzing session data and generating response…</span>
                      </div>
                    ) : turn.status === "error" ? (
                      <div className="rounded-[var(--radius-md)] border border-red-200 bg-red-50 p-4">
                        <div className="flex items-center gap-2 text-sm font-semibold text-red-800">
                          <AlertCircle className="size-4" />
                          <span>Response Failed</span>
                        </div>
                        <p className="mt-1 text-xs text-red-700">{turn.errorMessage}</p>
                        {canAskBackend ? (
                          <button
                            type="button"
                            onClick={() => retry(turn)}
                            className="mt-3 inline-flex min-h-[44px] items-center rounded-[var(--radius-sm)] bg-red-100 px-3 py-1.5 text-xs font-semibold text-red-800 hover:bg-red-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
                          >
                            Retry Question
                          </button>
                        ) : null}
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {/* Response Header */}
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-[var(--accent-strong)]">
                              DSP Copilot Engine
                            </span>
                            <span className="text-[11px] text-[var(--muted)]">· /copilot/complete</span>
                          </div>
                          {turn.unavailable ? (
                            <Badge tone="warning">Provider Unavailable</Badge>
                          ) : (
                            <Badge tone="success">Validated</Badge>
                          )}
                        </div>

                        {/* Answer Content */}
                        <div className="text-sm leading-relaxed text-[var(--fg)]">
                          {turn.content}
                        </div>

                        {/* Evidence & Sources Sub-panel */}
                        <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-3 text-xs">
                          <div className="grid gap-3 sm:grid-cols-2">
                            <div>
                              <p className="font-semibold uppercase tracking-wider text-[var(--muted)]">
                                Supporting Evidence
                              </p>
                              {turn.citations?.length ? (
                                <ul className="mt-1 list-inside list-disc space-y-0.5 text-[var(--fg)]">
                                  {turn.citations.map((c) => (
                                    <li key={c}>{c}</li>
                                  ))}
                                </ul>
                              ) : (
                                <p className="mt-1 text-[var(--muted)]">Evidence unavailable</p>
                              )}
                            </div>

                            <div>
                              <p className="font-semibold uppercase tracking-wider text-[var(--muted)]">
                                Source Verification
                              </p>
                              <p className="mt-1 text-[var(--muted)]">
                                Source unavailable: External document retrieval and multi-source citations are bounded by provider availability.
                              </p>
                            </div>
                          </div>

                          {turn.limitations?.length ? (
                            <div className="mt-3 border-t border-[var(--border)] pt-2 text-[11px] text-[var(--muted)]">
                              <span className="font-semibold text-[var(--fg)]">Limitations:</span>{" "}
                              {turn.limitations.join(" · ")}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    )}
                  </article>
                ))
              )}
              <div ref={bottomRef} />
            </div>

            {/* Suggested Follow-up Actions */}
            <div className="space-y-2 pt-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                Suggested Follow-up Inquiries
              </p>
              <div className="grid gap-2 sm:grid-cols-2" aria-label="Suggested follow-up questions">
                {RESEARCH_SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion.questionId}
                    type="button"
                    onClick={() => submitQuestion(suggestion.questionId, suggestion.label)}
                    disabled={askMutation.isPending}
                    className="flex min-h-[44px] flex-col items-start justify-center rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3.5 py-2 text-left hover:border-[var(--accent)] hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:opacity-50"
                  >
                    <span className="text-xs font-semibold text-[var(--fg)]">
                      {suggestion.label}
                    </span>
                    <span className="text-[11px] text-[var(--muted)]">
                      {suggestion.description}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Composer Input */}
            <div className="pt-2">
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  submitQuestion("freeform", draft);
                }}
                className="space-y-2 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-3 shadow-[var(--shadow-sm)]"
              >
                <label htmlFor="research-composer" className="block text-xs font-semibold text-[var(--muted)]">
                  Ask a follow-up question regarding {ticker}
                </label>
                <div className="flex items-end gap-3">
                  <textarea
                    id="research-composer"
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    onKeyDown={onComposerKeyDown}
                    placeholder={`e.g. "Explain the valuation assumptions" or "What are the primary operational risks?"`}
                    rows={2}
                    className="min-h-[44px] min-w-0 flex-1 resize-none rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface-2)] p-2.5 text-sm leading-snug text-[var(--fg)] placeholder:text-[var(--muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                    aria-label="Ask a follow-up question"
                  />
                  <button
                    type="submit"
                    disabled={!draft.trim() || askMutation.isPending}
                    aria-label="Send inquiry"
                    className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-[var(--radius-md)] bg-[var(--accent)] px-4 font-semibold text-white hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:opacity-40"
                  >
                    <ArrowUp className="size-4" />
                  </button>
                </div>
                <div className="flex flex-wrap items-center justify-between text-[11px] text-[var(--muted)]">
                  <span>Press <kbd className="rounded border px-1">Enter</kbd> to submit, <kbd className="rounded border px-1">Shift+Enter</kbd> for newline</span>
                  <span>Institutional Engine · No synthetic AI values</span>
                </div>
              </form>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

export default ResultConversation;

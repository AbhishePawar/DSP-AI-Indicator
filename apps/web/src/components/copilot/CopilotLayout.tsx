"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ds";
import { ChatWindow } from "@/components/copilot/ChatWindow";
import { ComparisonPanel } from "@/components/copilot/ComparisonPanel";
import { ConversationHistory } from "@/components/copilot/ConversationHistory";
import { ResearchContextPanel } from "@/components/copilot/ResearchContextPanel";
import { SuggestedQuestions } from "@/components/copilot/SuggestedQuestions";
import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import { api } from "@/lib/api/client";
import {
  appendExchange,
  conversationToMarkdown,
  createConversation,
} from "@/lib/copilot/conversation";
import { buildCopilotContext } from "@/lib/copilot/contextBuilder";
import { modeForQuestion } from "@/lib/copilot/modeMap";
import { SUGGESTED_QUESTIONS } from "@/lib/copilot/questions";
import { archiveResearchSession, listArchivedSessions } from "@/lib/copilot/sessionArchive";
import type {
  CopilotConversation,
  CopilotIntent,
  CopilotResearchContext,
  ResearchCitationId,
  SuggestedQuestion,
} from "@/lib/copilot/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { usePersistence } from "@/providers/PersistenceProvider";
import { loadResearchSession } from "@/lib/research/sessionStore";

function asIntent(value: string | undefined): CopilotIntent {
  if (!value) return "unknown";
  const known: CopilotIntent[] = [
    "explain_valuation",
    "explain_recommendation",
    "explain_moat",
    "explain_management",
    "summarise_strengths",
    "summarise_weaknesses",
    "explain_committee",
    "explain_financial_strength",
    "explain_earnings_quality",
    "explain_growth_quality",
    "explain_margin_of_safety",
    "compare_companies",
    "explain_risk",
    "analyze_portfolio",
    "document_qa",
    "investment_memo",
    "buffett",
    "unknown",
  ];
  return known.includes(value as CopilotIntent)
    ? (value as CopilotIntent)
    : "unknown";
}

export function CopilotLayout() {
  const { status: authStatus, session } = useAuth();
  const { persistCopilotConversations } = usePersistence();
  const [conversations, setConversations] = useState<CopilotConversation[]>(
    () => [createConversation("Research Copilot")],
  );
  const [activeId, setActiveId] = useState<string | null>(null);
  const [serverConversationId, setServerConversationId] = useState<string | null>(
    null,
  );
  const [draft, setDraft] = useState("");
  const [typing, setTyping] = useState(false);
  const [streamingHint, setStreamingHint] = useState<string | null>(null);
  const [context, setContext] = useState<CopilotResearchContext>({
    ticker: null,
    company: null,
    exchange: null,
    hasSession: false,
    comparableTickers: [],
    canCompare: false,
  });
  const [request, setRequest] = useState<AnalyseRequest | null>(null);
  const [response, setResponse] = useState<AnalyseResponse | null>(null);
  const [secondaryRequest, setSecondaryRequest] =
    useState<AnalyseRequest | null>(null);
  const [secondaryResponse, setSecondaryResponse] =
    useState<AnalyseResponse | null>(null);
  const [latestCitations, setLatestCitations] = useState<
    ResearchCitationId[] | undefined
  >(undefined);
  const [memoryNote, setMemoryNote] = useState<string | null>(null);

  useEffect(() => {
    const sessionRow = loadResearchSession();
    if (sessionRow) {
      archiveResearchSession(sessionRow);
    }
    const archive = listArchivedSessions();
    const secondary =
      archive.find(
        (item) =>
          sessionRow &&
          item.ticker.toUpperCase() !== sessionRow.ticker.toUpperCase(),
      ) ?? null;

    if (sessionRow) {
      const comparableTickers = archive
        .map((item) => item.ticker)
        .filter(
          (ticker, index, all) =>
            all.findIndex((t) => t.toUpperCase() === ticker.toUpperCase()) ===
            index,
        );
      setContext({
        ticker: sessionRow.ticker,
        company: sessionRow.company,
        exchange: sessionRow.exchange,
        hasSession: true,
        comparableTickers,
        canCompare: comparableTickers.length >= 2,
      });
      setRequest(sessionRow.request);
      setResponse(sessionRow.response);
    }

    if (secondary) {
      setSecondaryRequest(secondary.request);
      setSecondaryResponse(secondary.response);
    }

    setActiveId((current) => current ?? conversations[0]?.id ?? null);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- bootstrap once
  }, []);

  useEffect(() => {
    if (authStatus !== "authenticated") return;
    void api
      .copilotHistoryList({ token: session?.accessToken })
      .then((payload) => {
        const count = payload.conversations?.length ?? 0;
        setMemoryNote(
          count > 0
            ? `Server memory: ${count} conversation(s) retained.`
            : "Server memory ready — conversations persist for this API process.",
        );
      })
      .catch(() => {
        setMemoryNote("Server memory unavailable — local conversation retained.");
      });
  }, [authStatus, session?.accessToken]);

  const active = useMemo(
    () => conversations.find((c) => c.id === activeId) ?? conversations[0] ?? null,
    [conversations, activeId],
  );

  const primaryContext = useMemo(
    () => buildCopilotContext(request, response),
    [request, response],
  );
  const secondaryContext = useMemo(
    () => buildCopilotContext(secondaryRequest, secondaryResponse),
    [secondaryRequest, secondaryResponse],
  );

  const latestAssistant = useMemo(() => {
    if (!active) return null;
    const assistants = active.messages.filter((m) => m.role === "assistant");
    return assistants.at(-1) ?? null;
  }, [active]);

  const visibleQuestions = useMemo(() => {
    if (context.canCompare) return SUGGESTED_QUESTIONS;
    return SUGGESTED_QUESTIONS.filter((q) => q.id !== "compare_companies");
  }, [context.canCompare]);

  const respond = useCallback(
    (userText: string, questionId: SuggestedQuestion["id"] | "freeform") => {
      if (!active || typing) return;
      setTyping(true);
      setDraft("");
      setStreamingHint("Orchestrating engines…");

      const mode = modeForQuestion(questionId);
      const analysePayload =
        response && typeof response === "object"
          ? ((response as { payload?: Record<string, unknown> }).payload ??
            (response as unknown as Record<string, unknown>))
          : null;
      const secondaryPayload =
        secondaryResponse && typeof secondaryResponse === "object"
          ? ((secondaryResponse as { payload?: Record<string, unknown> }).payload ??
            (secondaryResponse as unknown as Record<string, unknown>))
          : null;

      void api
        .copilotV2Chat(
          {
            message: userText,
            mode,
            conversation_id: serverConversationId,
            symbol: context.ticker,
            symbols: context.ticker
              ? [
                  context.ticker,
                  ...context.comparableTickers.filter(
                    (t) => t.toUpperCase() !== context.ticker?.toUpperCase(),
                  ),
                ]
              : undefined,
            analyse_response: analysePayload,
            secondary_analyse_response: secondaryPayload,
            workspace: "company_workspace",
            buffett_mode: questionId === "buffett",
          },
          { token: session?.accessToken },
        )
        .then((payload) => {
          const result = payload.result;
          const answer = result?.answer || "Data unavailable.";
          setStreamingHint(null);
          setLatestCitations(undefined);
          if (result?.conversation_id) {
            setServerConversationId(result.conversation_id);
          }
          setConversations((current) =>
            current.map((conversation) =>
              conversation.id === active.id
                ? appendExchange(conversation, userText, answer, {
                    intent: asIntent(result?.intent),
                    ticker: context.ticker,
                    sources: result?.sources,
                    markdown: true,
                    serverConversationId: result?.conversation_id,
                  })
                : conversation,
            ),
          );
          if (result?.conversation_id) {
            setActiveId((id) =>
              id === active.id ? result.conversation_id! : id,
            );
          }
          setTyping(false);
        })
        .catch(() => {
          setStreamingHint(null);
          setConversations((current) =>
            current.map((conversation) =>
              conversation.id === active.id
                ? appendExchange(conversation, userText, "Data unavailable.", {
                    intent: "unknown",
                    ticker: context.ticker,
                    markdown: true,
                  })
                : conversation,
            ),
          );
          setTyping(false);
        });
    },
    [
      active,
      context.comparableTickers,
      context.ticker,
      response,
      secondaryResponse,
      serverConversationId,
      session?.accessToken,
      typing,
    ],
  );

  function handleSuggested(question: SuggestedQuestion) {
    respond(question.label, question.id);
  }

  function handleSend(text: string) {
    respond(text, "freeform");
  }

  function handleCompare() {
    respond("Compare companies.", "compare_companies");
  }

  function handleNew() {
    const next = createConversation();
    setConversations((current) => [next, ...current]);
    setActiveId(next.id);
    setServerConversationId(null);
    setDraft("");
    setLatestCitations(undefined);
  }

  async function handleDeleteActive() {
    if (!active) return;
    if (serverConversationId) {
      try {
        await api.copilotHistoryDelete(serverConversationId, {
          token: session?.accessToken,
        });
      } catch {
        // local delete still proceeds
      }
    }
    setConversations((current) => {
      const next = current.filter((c) => c.id !== active.id);
      return next.length ? next : [createConversation()];
    });
    setActiveId(null);
    setServerConversationId(null);
  }

  function handleExport() {
    if (!active) return;
    const markdown = conversationToMarkdown(active);
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${active.title.replace(/\s+/g, "-").slice(0, 40) || "copilot"}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  useEffect(() => {
    if (authStatus !== "authenticated") return;
    persistCopilotConversations(conversations);
  }, [conversations, authStatus, persistCopilotConversations]);

  return (
    <div className="space-y-6" data-testid="copilot-v2-layout">
      <PageHeader
        title="AI Research Copilot 2.0"
        description="Conversational orchestration over existing engines. No duplicated calculations. Missing data stays Data unavailable."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" onClick={handleExport}>
              Export
            </Button>
            <Button size="sm" variant="secondary" onClick={handleDeleteActive}>
              Delete
            </Button>
          </div>
        }
      />

      {!context.hasSession ? (
        <Alert tone="info" title="No research session">
          Run an analysis first for valuation/committee explanations. Portfolio,
          document, and freeform company questions can still use Copilot 2.0
          orchestration.
        </Alert>
      ) : (
        <Alert tone="info" title="Research context loaded">
          Explaining {context.company ?? context.ticker} ({context.ticker})
          {context.canCompare
            ? ` · Compare ready with ${context.comparableTickers
                .filter(
                  (t) => t.toUpperCase() !== context.ticker?.toUpperCase(),
                )
                .join(", ")}`
            : ""}
          .
        </Alert>
      )}

      {memoryNote ? (
        <p className="text-xs text-[var(--muted)]" data-testid="copilot-memory-note">
          {memoryNote}
          {streamingHint ? ` · ${streamingHint}` : ""}
        </p>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(16rem,20rem)_minmax(0,1fr)]">
        <aside className="space-y-4">
          <ConversationHistory
            conversations={conversations}
            activeId={active?.id ?? null}
            onSelect={setActiveId}
            onNew={handleNew}
          />
          <SuggestedQuestions
            questions={visibleQuestions}
            onSelect={handleSuggested}
            disabled={typing}
          />
        </aside>

        <div className="min-w-0 space-y-4">
          <ChatWindow
            messages={active?.messages ?? []}
            typing={typing}
            draft={draft}
            onDraftChange={setDraft}
            onSend={handleSend}
            disabled={typing}
            ticker={context.ticker}
          />
          <ResearchContextPanel
            context={context}
            latestAnswer={latestAssistant?.content ?? null}
            latestCitations={
              latestAssistant?.citations ?? latestCitations
            }
            onCompare={handleCompare}
          />
          <ComparisonPanel
            primary={primaryContext}
            secondary={secondaryContext}
            available={context.canCompare}
          />
        </div>
      </div>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { ChatWindow } from "@/components/copilot/ChatWindow";
import { ComparisonPanel } from "@/components/copilot/ComparisonPanel";
import { ConversationHistory } from "@/components/copilot/ConversationHistory";
import { ResearchContextPanel } from "@/components/copilot/ResearchContextPanel";
import { SuggestedQuestions } from "@/components/copilot/SuggestedQuestions";
import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import {
  appendExchange,
  createConversation,
} from "@/lib/copilot/conversation";
import { buildCopilotContext } from "@/lib/copilot/contextBuilder";
import { buildAIRequest } from "@/lib/ai/mappers";
import { useAIService } from "@/providers/AIProviderContext";
import { SUGGESTED_QUESTIONS } from "@/lib/copilot/questions";
import { archiveResearchSession, listArchivedSessions } from "@/lib/copilot/sessionArchive";
import type {
  CopilotConversation,
  CopilotResearchContext,
  ResearchCitationId,
  SuggestedQuestion,
} from "@/lib/copilot/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { usePersistence } from "@/providers/PersistenceProvider";

import { loadResearchSession } from "@/lib/research/sessionStore";

export function CopilotLayout() {
  const { status: authStatus } = useAuth();
  const { persistCopilotConversations } = usePersistence();
  const aiService = useAIService();
  const [conversations, setConversations] = useState<CopilotConversation[]>(
    () => [createConversation("Research Copilot")],
  );
  const [activeId, setActiveId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [typing, setTyping] = useState(false);
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

  useEffect(() => {
    const session = loadResearchSession();
    if (session) {
      archiveResearchSession(session);
    }
    const archive = listArchivedSessions();
    const secondary =
      archive.find(
        (item) =>
          session &&
          item.ticker.toUpperCase() !== session.ticker.toUpperCase(),
      ) ?? null;

    if (session) {
      const comparableTickers = archive
        .map((item) => item.ticker)
        .filter(
          (ticker, index, all) =>
            all.findIndex((t) => t.toUpperCase() === ticker.toUpperCase()) ===
            index,
        );
      setContext({
        ticker: session.ticker,
        company: session.company,
        exchange: session.exchange,
        hasSession: true,
        comparableTickers,
        canCompare: comparableTickers.length >= 2,
      });
      setRequest(session.request);
      setResponse(session.response);
    }

    if (secondary) {
      setSecondaryRequest(secondary.request);
      setSecondaryResponse(secondary.response);
    }

    setActiveId((current) => current ?? conversations[0]?.id ?? null);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- bootstrap once
  }, []);

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

      window.setTimeout(() => {
        void aiService
          .complete(
            buildAIRequest({
              questionId,
              freeform: userText,
              request,
              response,
              secondaryRequest,
              secondaryResponse,
              lastIntent: active.context.lastIntent,
            }),
          )
          .then((composed) => {
            setLatestCitations(composed.citations);
            setConversations((current) =>
              current.map((conversation) =>
                conversation.id === active.id
                  ? appendExchange(conversation, userText, composed.content, {
                      citations: composed.citations,
                      intent: composed.intent,
                      ticker: context.ticker,
                    })
                  : conversation,
              ),
            );
            setTyping(false);
          });
      }, 350);
    },
    [
      active,
      aiService,
      context.ticker,
      request,
      response,
      secondaryRequest,
      secondaryResponse,
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
    setDraft("");
    setLatestCitations(undefined);
  }

  useEffect(() => {
    if (authStatus !== "authenticated") return;
    persistCopilotConversations(conversations);
  }, [conversations, authStatus, persistCopilotConversations]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Research Copilot"
        description="Context-aware explainability over existing research fields. No LLM. No invented numbers."
      />

      {!context.hasSession ? (
        <Alert tone="info" title="No research session">
          Run an analysis first. Copilot answers only from session research
          fields and will say when information is unavailable.
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

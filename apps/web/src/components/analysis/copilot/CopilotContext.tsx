"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { AnalysisWorkspaceView } from "@/lib/analysis/types";
import {
  buildCopilotAnswer,
  createSessionMemory,
  resolveCopilotAction,
  uid,
  type CopilotAction,
  type CopilotContextSnapshot,
  type CopilotMessage,
  type CopilotSessionMemory,
} from "@/lib/analysis/sprint6Copilot";

type AskArgs = {
  action?: CopilotAction;
  text?: string;
  metricId?: string;
  metricTitle?: string;
  sectionId?: string;
  graphNodeId?: string;
};

type CopilotContextValue = {
  open: boolean;
  setOpen: (v: boolean) => void;
  messages: CopilotMessage[];
  memory: CopilotSessionMemory;
  thinking: boolean;
  ask: (args: AskArgs) => void;
  setSelectedSection: (id: string | null) => void;
  setSelectedGraphNode: (id: string | null) => void;
  clearConversation: () => void;
};

const CopilotContext = createContext<CopilotContextValue | null>(null);

export function CopilotProvider({
  view,
  children,
}: {
  view: AnalysisWorkspaceView;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<CopilotMessage[]>(() => [
    {
      id: uid("sys"),
      role: "system",
      text: "Research Copilot explains DSP Research only. It does not produce Buy/Sell advice or invent numbers.",
      createdAt: Date.now(),
    },
  ]);
  const [memory, setMemory] = useState<CopilotSessionMemory>(() =>
    createSessionMemory(view),
  );
  const [thinking, setThinking] = useState(false);

  const setSelectedSection = useCallback((id: string | null) => {
    setMemory((m) => ({
      ...m,
      selectedSectionId: id,
      expandedSections: id
        ? Array.from(new Set([...m.expandedSections, id])).slice(-12)
        : m.expandedSections,
    }));
  }, []);

  const setSelectedGraphNode = useCallback((id: string | null) => {
    setMemory((m) => ({ ...m, selectedGraphNodeId: id }));
  }, []);

  const clearConversation = useCallback(() => {
    setMessages([
      {
        id: uid("sys"),
        role: "system",
        text: "Conversation cleared (session only). DSP Research is unchanged.",
        createdAt: Date.now(),
      },
    ]);
    setMemory(createSessionMemory(view));
  }, [view]);

  useEffect(() => {
    const syncHash = () => {
      const id = window.location.hash.replace(/^#/, "") || null;
      if (id) {
        setMemory((m) => ({
          ...m,
          selectedSectionId: id,
          expandedSections: Array.from(new Set([...m.expandedSections, id])).slice(
            -12,
          ),
          companyLabel:
            view.snapshot.ticker.value ??
            view.snapshot.companyName.value ??
            m.companyLabel,
        }));
      }
    };
    syncHash();
    window.addEventListener("hashchange", syncHash);
    return () => window.removeEventListener("hashchange", syncHash);
  }, [view.snapshot.ticker.value, view.snapshot.companyName.value]);

  const ask = useCallback(
    (args: AskArgs) => {
      setOpen(true);
      const text =
        args.text ??
        (args.action ? `Action: ${args.action}` : "Explain this research");
      const action = resolveCopilotAction(args.action ?? "free_text", text);

      setMemory((m) => {
        const next: CopilotSessionMemory = {
          ...m,
          companyLabel:
            view.snapshot.ticker.value ??
            view.snapshot.companyName.value ??
            m.companyLabel,
          recentQuestions: [text, ...m.recentQuestions].slice(0, 20),
          selectedMetricId: args.metricId ?? m.selectedMetricId,
          selectedSectionId: args.sectionId ?? m.selectedSectionId,
          selectedGraphNodeId: args.graphNodeId ?? m.selectedGraphNodeId,
          expandedSections: args.sectionId
            ? Array.from(new Set([...m.expandedSections, args.sectionId])).slice(-12)
            : m.expandedSections,
        };

        const ctx: CopilotContextSnapshot = {
          sectionId: next.selectedSectionId,
          graphNodeId: next.selectedGraphNodeId,
          metricId: next.selectedMetricId,
          metricTitle: args.metricTitle ?? null,
        };

        setMessages((prev) =>
          [
            ...prev,
            {
              id: uid("user"),
              role: "user" as const,
              text,
              action,
              createdAt: Date.now(),
            },
          ].slice(-40),
        );
        setThinking(true);

        window.setTimeout(() => {
          const answer = buildCopilotAnswer(view, action, ctx, text);
          setMessages((prev) =>
            [
              ...prev,
              {
                id: uid("asst"),
                role: "assistant" as const,
                text: answer.shortAnswer,
                action,
                answer,
                createdAt: Date.now(),
              },
            ].slice(-40),
          );
          setThinking(false);
        }, 220);

        return next;
      });
    },
    [view],
  );

  const value = useMemo(
    () => ({
      open,
      setOpen,
      messages,
      memory,
      thinking,
      ask,
      setSelectedSection,
      setSelectedGraphNode,
      clearConversation,
    }),
    [
      open,
      messages,
      memory,
      thinking,
      ask,
      setSelectedSection,
      setSelectedGraphNode,
      clearConversation,
    ],
  );

  return (
    <CopilotContext.Provider value={value}>{children}</CopilotContext.Provider>
  );
}

export function useCopilot(): CopilotContextValue {
  const ctx = useContext(CopilotContext);
  if (!ctx) {
    throw new Error("useCopilot must be used within CopilotProvider");
  }
  return ctx;
}

export function useCopilotOptional(): CopilotContextValue | null {
  return useContext(CopilotContext);
}

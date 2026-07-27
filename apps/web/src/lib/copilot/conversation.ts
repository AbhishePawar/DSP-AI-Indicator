import type {
  ConversationContextState,
  CopilotConversation,
  CopilotIntent,
  CopilotMessage,
  ResearchCitationId,
} from "./types";

export function createMessage(
  role: CopilotMessage["role"],
  content: string,
  citations?: ResearchCitationId[],
): CopilotMessage {
  return {
    id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role,
    content,
    createdAt: new Date().toISOString(),
    citations,
  };
}

export function emptyConversationContext(): ConversationContextState {
  return { lastIntent: null, lastTicker: null };
}

export function createConversation(title = "New conversation"): CopilotConversation {
  const now = new Date().toISOString();
  return {
    id: `conv-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    title,
    createdAt: now,
    updatedAt: now,
    context: emptyConversationContext(),
    messages: [
      createMessage(
        "assistant",
        "Ask a suggested question to explain the latest research session. I only restate fields already returned by the API — I never invent numbers.",
      ),
    ],
  };
}

export function appendExchange(
  conversation: CopilotConversation,
  userText: string,
  assistantText: string,
  options?: {
    citations?: ResearchCitationId[];
    intent?: CopilotIntent | null;
    ticker?: string | null;
  },
): CopilotConversation {
  const user = createMessage("user", userText);
  const assistant = createMessage(
    "assistant",
    assistantText,
    options?.citations,
  );
  return {
    ...conversation,
    title:
      conversation.messages.filter((m) => m.role === "user").length === 0
        ? userText.slice(0, 48)
        : conversation.title,
    updatedAt: new Date().toISOString(),
    context: {
      lastIntent: options?.intent ?? conversation.context.lastIntent,
      lastTicker: options?.ticker ?? conversation.context.lastTicker,
    },
    messages: [...conversation.messages, user, assistant],
  };
}

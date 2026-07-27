/**
 * Compatibility wrapper — routes through context builder + intent + composer.
 */

import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import { composeAnswer } from "./answerComposer";
import { buildCopilotContext } from "./contextBuilder";
import { intentFromSuggestedId, resolveIntent } from "./intentResolver";
import type { CopilotComposedAnswer, SuggestedQuestionId } from "./types";

export function buildPlaceholderAnswer(
  questionId: SuggestedQuestionId | "freeform",
  options: {
    request: AnalyseRequest | null;
    response: AnalyseResponse | null;
    freeform?: string;
    secondaryRequest?: AnalyseRequest | null;
    secondaryResponse?: AnalyseResponse | null;
    lastIntent?: import("./types").CopilotIntent | null;
  },
): string {
  return composeCopilotAnswer(questionId, options).content;
}

export function composeCopilotAnswer(
  questionId: SuggestedQuestionId | "freeform",
  options: {
    request: AnalyseRequest | null;
    response: AnalyseResponse | null;
    freeform?: string;
    secondaryRequest?: AnalyseRequest | null;
    secondaryResponse?: AnalyseResponse | null;
    lastIntent?: import("./types").CopilotIntent | null;
  },
): CopilotComposedAnswer {
  const intent =
    questionId === "freeform"
      ? resolveIntent(options.freeform ?? "", {
          lastIntent: options.lastIntent,
        })
      : intentFromSuggestedId(questionId);

  const primary = buildCopilotContext(options.request, options.response);
  const secondary = buildCopilotContext(
    options.secondaryRequest ?? null,
    options.secondaryResponse ?? null,
  );

  return composeAnswer(intent, primary, secondary);
}

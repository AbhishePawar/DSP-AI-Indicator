import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import type { CopilotIntent, SuggestedQuestionId } from "@/lib/copilot/types";
import type { AIRequest } from "./types";

export function buildAIRequest(input: {
  questionId: SuggestedQuestionId | "freeform";
  freeform?: string;
  request: AnalyseRequest | null;
  response: AnalyseResponse | null;
  secondaryRequest?: AnalyseRequest | null;
  secondaryResponse?: AnalyseResponse | null;
  lastIntent?: CopilotIntent | null;
}): AIRequest {
  return {
    questionId: input.questionId,
    freeform: input.freeform,
    primary: {
      request: input.request,
      response: input.response,
    },
    secondary:
      input.secondaryRequest != null || input.secondaryResponse != null
        ? {
            request: input.secondaryRequest ?? null,
            response: input.secondaryResponse ?? null,
          }
        : undefined,
    lastIntent: input.lastIntent,
  };
}

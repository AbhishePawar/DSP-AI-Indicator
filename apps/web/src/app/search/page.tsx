import { redirect } from "next/navigation";
import {
  buildAnalysisUrl,
  parseAnalysisIntent,
  parseResearchMode,
} from "@/lib/analysis/intents";

type SearchParams = Promise<{
  q?: string;
  query?: string;
  symbol?: string;
  ticker?: string;
  mode?: string;
  intent?: string;
  exchange?: string;
}>;

/** L1.0 route — preserves query, mode, and intent, redirecting to Company Analysis (L1.1). */
export default async function SearchRedirectPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const resolvedParams = searchParams ? await searchParams : {};
  const rawSymbol =
    resolvedParams.symbol ||
    resolvedParams.ticker ||
    resolvedParams.q ||
    resolvedParams.query ||
    "";
  const mode = parseResearchMode(resolvedParams.mode, resolvedParams.intent);
  const intent = parseAnalysisIntent(resolvedParams.intent ?? null);
  const exchange = resolvedParams.exchange;

  if (rawSymbol.trim()) {
    const baseUrl = buildAnalysisUrl({
      symbol: rawSymbol.trim(),
      mode,
      intent,
    });
    const finalUrl = exchange?.trim()
      ? `${baseUrl}&exchange=${encodeURIComponent(exchange.trim().toUpperCase())}`
      : baseUrl;
    redirect(finalUrl);
  }

  redirect("/analysis");
}

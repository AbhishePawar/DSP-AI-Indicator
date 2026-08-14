/**
 * Contradictory Evidence Panel — never hide conflicts.
 * Supporting + contradictory from existing research fields only.
 */

import type { ResearchView } from "@/lib/research/mapResearchView";
import {
  COVERAGE_UNAVAILABLE,
  DATA_UNAVAILABLE,
} from "./constants";
import type { ContradictoryEvidenceCell } from "./types";

function uniqueNonEmpty(items: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of items) {
    const t = raw.trim();
    if (!t) continue;
    const key = t.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(t);
  }
  return out;
}

export function mapContradictoryEvidence(
  views: ResearchView[],
): ContradictoryEvidenceCell[] {
  return views.map((v) => {
    const supporting = uniqueNonEmpty([
      ...v.committee.supportingReasons,
      ...v.strengths,
      ...(v.explainability.modules
        .filter((m) => {
          const c = m.confidence?.toLowerCase?.() ?? "";
          return c.includes("high") || c.includes("strong");
        })
        .map((m) => `${m.title}: ${m.oneLineSummary}`)
        .filter((s) => !s.toLowerCase().includes("unavailable"))),
    ]);

    const contradictory = uniqueNonEmpty([
      ...v.committee.opposingReasons,
      ...v.weaknesses,
      ...v.risks,
      ...(v.limitations ?? []),
      ...(v.errors ?? []).map((e) =>
        typeof e === "string" ? e : String(e),
      ),
    ]);

    const succeeded = v.stages.filter((s) => s.status === "succeeded").length;
    const total = v.stages.length;
    const coverage =
      total === 0
        ? COVERAGE_UNAVAILABLE
        : `${succeeded}/${total} stages succeeded`;

    const confidence =
      v.recommendationConfidence != null
        ? `${Math.round(v.recommendationConfidence * 100)}%`
        : DATA_UNAVAILABLE;

    const sourceBits = [
      v.correlationId ? `correlation_id=${v.correlationId}` : null,
      v.pipelineVersion ? `pipeline=${v.pipelineVersion}` : null,
      v.platformVersion ? `platform=${v.platformVersion}` : null,
    ].filter(Boolean) as string[];

    return {
      symbol: v.ticker,
      supporting:
        supporting.length > 0
          ? supporting
          : ["Data unavailable. — no supporting evidence fields on this pack."],
      contradictory:
        contradictory.length > 0
          ? contradictory
          : [
              "Data unavailable. — no contradictory evidence fields on this pack. Absence of listed conflicts is not evidence of absence.",
            ],
      coverage,
      confidence,
      sourceQuality:
        sourceBits.length > 0 ? sourceBits.join("; ") : DATA_UNAVAILABLE,
      honestyNote:
        "Conflicts are never hidden. Both supporting and contradictory lists are shown when present on existing research outputs.",
    };
  });
}

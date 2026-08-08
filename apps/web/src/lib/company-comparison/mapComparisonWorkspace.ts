/**
 * EPIC-012/013/013A — Compose Institutional Company Comparison workspace model.
 * Pure presentation from mapped ResearchView slots + optional RI overlays.
 * No analytical recalculation.
 */

import type { ResearchView } from "@/lib/research/mapResearchView";
import {
  ANALYSIS_UNAVAILABLE,
  BUFFETT_DISCLAIMER,
  COVERAGE_UNAVAILABLE,
  DATA_UNAVAILABLE,
  WORKSPACE_DISCLAIMER,
} from "./constants";
import { INSTITUTIONAL_UX_QUESTIONS } from "./decisionWorkflow";
import { mapBuffettPreference } from "./mapBuffettPreference";
import { mapCommitteeMemo } from "./mapCommitteeMemo";
import { mapContradictoryEvidence } from "./mapContradictoryEvidence";
import { mapEvidenceStrengthMeters } from "./mapEvidenceStrength";
import { mapExecutiveScorecard } from "./mapExecutiveScorecard";
import { mapSectorContext, type CatalogueSectorLookup } from "./mapSectorContext";
import { mapSensitivityPanel } from "./mapSensitivity";
import { mapTradeOffs } from "./mapTradeOffs";
import { mapWhyNotAnalysis } from "./mapWhyNotAnalysis";
import { mapWinnerMatrix } from "./mapWinnerMatrix";
import {
  honestDisplay,
  parseExistingScore,
} from "./ranking";
import type {
  CompanyIntelligenceOverlay,
  ComparisonCompanySlot,
  ComparisonWorkspaceModel,
  EvidenceQualityCell,
  ExecutiveSummaryView,
  ExplainabilityCompareCell,
  HeatmapCell,
  PortfolioFitCell,
  ScenarioCompareCell,
  ValuationCompareCell,
} from "./types";
import type { WeightingProfileId } from "./weightingProfiles";

function methodStatus(
  view: ResearchView,
  methodName: string,
): string {
  const card = view.valuationTransparency.methods.find((m) =>
    m.methodName.toLowerCase().includes(methodName.toLowerCase()),
  );
  if (!card) return DATA_UNAVAILABLE;
  if (card.status === "Unavailable") return DATA_UNAVAILABLE;
  return honestDisplay(card.intrinsicValue);
}

function mapValuation(views: ResearchView[]): ValuationCompareCell[] {
  return views.map((v) => ({
    symbol: v.ticker,
    intrinsicValue: honestDisplay(v.valuation.intrinsicValue),
    price: honestDisplay(v.valuation.currentPrice),
    marginOfSafety: honestDisplay(v.valuation.marginOfSafety),
    dcf: methodStatus(v, "DCF"),
    relative: methodStatus(v, "Relative"),
    residualIncome: methodStatus(v, "Residual"),
    epv: methodStatus(v, "EPV"),
    overall: honestDisplay(v.ratings.modules.valuation.scoreOutOf10),
    confidence: honestDisplay(v.valuation.confidence),
    historical: DATA_UNAVAILABLE, // no historical valuation series on /analyse
  }));
}

function qualityRow(
  views: ResearchView[],
  pick: (v: ResearchView) => { score: string; label: string; confidence: string },
) {
  return views.map((v) => {
    const p = pick(v);
    return {
      symbol: v.ticker,
      score: honestDisplay(p.score),
      label: honestDisplay(p.label),
      confidence: honestDisplay(p.confidence),
    };
  });
}

function mapEvidence(views: ResearchView[]): EvidenceQualityCell[] {
  return views.map((v) => {
    const count = Object.values(v.evidenceCounts ?? {}).reduce(
      (a, b) => a + (typeof b === "number" ? b : 0),
      0,
    );
    const succeeded = v.stages.filter((s) => s.status === "succeeded").length;
    const total = v.stages.length;
    const coverage =
      total === 0
        ? COVERAGE_UNAVAILABLE
        : `${succeeded}/${total} stages succeeded`;
    return {
      symbol: v.ticker,
      evidenceCount: count > 0 ? String(count) : DATA_UNAVAILABLE,
      confidence:
        v.recommendationConfidence != null
          ? `${Math.round(v.recommendationConfidence * 100)}%`
          : DATA_UNAVAILABLE,
      coverage,
      freshness: v.analysedAt ?? DATA_UNAVAILABLE,
      sources: [
        `correlation_id=${v.correlationId ?? DATA_UNAVAILABLE}`,
        `pipeline=${v.pipelineVersion ?? DATA_UNAVAILABLE}`,
        `platform=${v.platformVersion ?? DATA_UNAVAILABLE}`,
      ],
      status: v.ok ? "ok" : "degraded",
    };
  });
}

function mapExplainability(views: ResearchView[]): ExplainabilityCompareCell[] {
  return views.map((v) => ({
    symbol: v.ticker,
    moduleSummaries: v.explainability.modules.slice(0, 8).map((m) => ({
      title: m.title,
      summary: honestDisplay(m.oneLineSummary),
      confidence: honestDisplay(m.confidence),
    })),
    overallExplanation: honestDisplay(v.ratings.overall.explanation),
  }));
}

function mapScenarios(views: ResearchView[]): ScenarioCompareCell[] {
  // Frozen /analyse DTO does not ship bull/base/bear scenario values.
  return views.map((v) => ({
    symbol: v.ticker,
    bull: ANALYSIS_UNAVAILABLE,
    base: ANALYSIS_UNAVAILABLE,
    bear: ANALYSIS_UNAVAILABLE,
  }));
}

function mapPortfolioFit(views: ResearchView[]): PortfolioFitCell[] {
  return views.map((v) => {
    const bq = parseExistingScore(v.businessQuality.score);
    const mos = parseExistingScore(
      v.valuation.marginOfSafety.replace("%", ""),
    );
    const growth = parseExistingScore(v.growth.score);
    return {
      symbol: v.ticker,
      quality:
        bq == null
          ? DATA_UNAVAILABLE
          : bq >= 70
            ? "Quality-aligned (from BQ score)"
            : "Lower quality signal (from BQ score)",
      value:
        mos == null
          ? DATA_UNAVAILABLE
          : mos >= 20
            ? "Value-aligned (from MoS)"
            : "Limited value cushion (from MoS)",
      growth:
        growth == null
          ? DATA_UNAVAILABLE
          : growth >= 65
            ? "Growth-aligned (from growth_quality)"
            : "Moderate/low growth signal",
      income: DATA_UNAVAILABLE, // no dividend yield on /analyse
      buffettFramework: honestDisplay(v.buffett.overallRating),
      note: "Portfolio-fit labels are style tags from existing research fields — not personalised advice.",
    };
  });
}

function mapHeatmap(
  views: ResearchView[],
  winnerMatrix: ReturnType<typeof mapWinnerMatrix>,
): HeatmapCell[] {
  const cells: HeatmapCell[] = [];
  for (const row of winnerMatrix) {
    for (const cell of row.cells) {
      let intensity: HeatmapCell["intensity"] = "unavailable";
      if (cell.numeric != null) {
        if (cell.medal === "gold" || cell.numeric >= 75) intensity = "high";
        else if (cell.numeric >= 55) intensity = "medium";
        else intensity = "low";
      }
      cells.push({
        symbol: cell.symbol,
        dimension: row.label,
        intensity,
        display: cell.display,
      });
    }
  }
  return cells;
}

function mapExecutive(
  views: ResearchView[],
  winnerMatrix: ReturnType<typeof mapWinnerMatrix>,
  tradeOffCount: number,
): ExecutiveSummaryView {
  if (views.length === 0) {
    return {
      overall: DATA_UNAVAILABLE,
      institutionalSummary: "No companies loaded for comparison.",
      winnerSummary: DATA_UNAVAILABLE,
      tradeOffs: [],
      confidence: DATA_UNAVAILABLE,
      coverage: COVERAGE_UNAVAILABLE,
      evidenceQuality: DATA_UNAVAILABLE,
    };
  }

  const leaders = winnerMatrix
    .filter((r) => r.leader !== DATA_UNAVAILABLE)
    .map((r) => `${r.label}: ${r.leader}`);

  const confidences = views
    .map((v) => v.recommendationConfidence)
    .filter((c): c is number => c != null);
  const avgConf =
    confidences.length === 0
      ? DATA_UNAVAILABLE
      : `${Math.round(
          (confidences.reduce((a, b) => a + b, 0) / confidences.length) * 100,
        )}% (mean of available recommendation confidences)`;

  const okCount = views.filter((v) => v.ok).length;

  return {
    overall: `Comparing ${views.map((v) => v.ticker).join(", ")} using existing /api/v1/analyse research packs. This workspace assists decision-making and never makes investment decisions for users.`,
    institutionalSummary: `Institutional presentation across ${views.length} companies. ${okCount}/${views.length} analyse responses reported ok=true. Ratings and Buffett-style preference panels remap existing outputs only.`,
    winnerSummary:
      leaders.length > 0
        ? `Dimension leaders (evidence-backed only): ${leaders.slice(0, 8).join("; ")}.`
        : DATA_UNAVAILABLE,
    tradeOffs:
      tradeOffCount > 0
        ? [`${tradeOffCount} evidence-backed trade-off notes generated from stage/score differences.`]
        : [DATA_UNAVAILABLE],
    confidence: avgConf,
    coverage: `${okCount}/${views.length} companies with successful analyse payloads`,
    evidenceQuality:
      views.some((v) => Object.keys(v.evidenceCounts ?? {}).length > 0)
        ? "Evidence counts present on at least one pack (see Evidence Comparison)."
        : DATA_UNAVAILABLE,
  };
}

export type MapComparisonOptions = {
  intelligence?: CompanyIntelligenceOverlay[];
  weightingProfileId?: WeightingProfileId;
  catalogue?: CatalogueSectorLookup[];
  personalNotes?: { kind: string; text: string }[];
  outstandingQuestions?: string[];
};

export function mapComparisonWorkspace(
  slots: ComparisonCompanySlot[],
  intelligenceOrOptions: CompanyIntelligenceOverlay[] | MapComparisonOptions = [],
): ComparisonWorkspaceModel {
  const options: MapComparisonOptions = Array.isArray(intelligenceOrOptions)
    ? { intelligence: intelligenceOrOptions }
    : intelligenceOrOptions;
  const intelligence = options.intelligence ?? [];
  const weightingProfileId = options.weightingProfileId ?? "equal";

  const ready = slots.filter((s) => s.status === "ready" && s.view != null);
  const views = ready.map((s) => s.view!);
  const winnerMatrix = mapWinnerMatrix(views);
  const tradeOffs = mapTradeOffs(views, winnerMatrix);
  const evidenceStrength = mapEvidenceStrengthMeters(views);
  const contradictoryEvidence = mapContradictoryEvidence(views);
  const whyNot = mapWhyNotAnalysis(views, winnerMatrix);
  const scorecard = mapExecutiveScorecard(
    views,
    winnerMatrix,
    evidenceStrength,
    weightingProfileId,
  );
  const committeeMemo = mapCommitteeMemo(
    views,
    winnerMatrix,
    tradeOffs,
    contradictoryEvidence,
    options.personalNotes ?? [],
    options.outstandingQuestions ?? [],
  );
  const sectorContext = mapSectorContext(views, options.catalogue ?? []);
  const sensitivity = mapSensitivityPanel(views);

  const coverageNotes = [
    WORKSPACE_DISCLAIMER,
    "Orchestration: client issues N frozen /api/v1/analyse calls (one per symbol). No backend comparison scoring.",
    "Weighting profiles change presentation emphasis only — analytical outputs and Winner Matrix numerics are unchanged.",
    ...slots
      .filter((s) => s.status === "error" || s.status === "unavailable")
      .map(
        (s) =>
          `${s.symbol}: ${s.error ?? DATA_UNAVAILABLE}`,
      ),
    views.length < 2
      ? "Select and compare at least two companies with successful research packs."
      : `${views.length} research packs ready for institutional comparison.`,
  ];

  const intelBySymbol = new Map(
    intelligence.map((i) => [i.symbol.toUpperCase(), i]),
  );

  return {
    kind: "institutional_company_comparison",
    version: "1.1",
    disclaimer: WORKSPACE_DISCLAIMER,
    buffettDisclaimer: BUFFETT_DISCLAIMER,
    generatedAt: new Date().toISOString(),
    symbols: slots.map((s) => s.symbol),
    slots: slots.map((s) => ({
      ...s,
      intelligence:
        s.intelligence ??
        intelBySymbol.get(s.symbol.toUpperCase()) ??
        null,
    })),
    executive: mapExecutive(views, winnerMatrix, tradeOffs.length),
    scorecard,
    winnerMatrix,
    tradeOffs,
    valuation: mapValuation(views),
    qualityModules: {
      businessQuality: qualityRow(views, (v) => ({
        score: v.businessQuality.score,
        label: v.businessQuality.label,
        confidence: v.businessQuality.confidence,
      })),
      management: qualityRow(views, (v) => ({
        score: v.management.score,
        label: v.management.label,
        confidence: v.management.confidence,
      })),
      moat: qualityRow(views, (v) => ({
        score: v.moat.score,
        label: v.moat.label,
        confidence: v.moat.confidence,
      })),
      risk: qualityRow(views, (v) => ({
        score: v.ratings.modules.riskAssessment.scoreOutOf10,
        label: v.ratings.modules.riskAssessment.grade,
        confidence: v.ratings.modules.riskAssessment.confidence,
      })),
      financial: qualityRow(views, (v) => ({
        score: v.financialStrength.score,
        label: v.financialStrength.label,
        confidence: v.financialStrength.confidence,
      })),
    },
    evidence: mapEvidence(views),
    evidenceStrength,
    contradictoryEvidence,
    whyNot,
    committeeMemo,
    sectorContext,
    sensitivity,
    explainability: mapExplainability(views),
    intelligence: views.map((v) => {
      const hit = intelBySymbol.get(v.ticker.toUpperCase());
      return (
        hit ?? {
          symbol: v.ticker,
          overallAccuracy: DATA_UNAVAILABLE,
          recommendationAccuracy: DATA_UNAVAILABLE,
          calibrationStatus: DATA_UNAVAILABLE,
          timelineCount: DATA_UNAVAILABLE,
          freshness: DATA_UNAVAILABLE,
          coverage: COVERAGE_UNAVAILABLE,
          source: "unavailable" as const,
        }
      );
    }),
    buffettPreference: mapBuffettPreference(views),
    heatmap: mapHeatmap(views, winnerMatrix),
    scenarios: mapScenarios(views),
    portfolioFit: mapPortfolioFit(views),
    coverageNotes,
    weightingProfileId,
    institutionalQuestions: [...INSTITUTIONAL_UX_QUESTIONS],
  };
}

/** Extract RI overlay fields from loosely typed EPIC-011B API payloads. */
export function mapIntelligenceOverlay(
  symbol: string,
  performance: Record<string, unknown> | null | undefined,
  calibration: Record<string, unknown> | null | undefined,
  timeline: { total?: number; timeline?: unknown[] } | null | undefined,
): CompanyIntelligenceOverlay {
  const dash = (performance?.dashboard ?? performance) as
    | Record<string, unknown>
    | undefined;
  const cal = (calibration?.calibration ?? calibration) as
    | Record<string, unknown>
    | undefined;
  const drift = cal?.drift as Record<string, unknown> | undefined;
  const coverage = dash?.coverage as Record<string, unknown> | undefined;

  const numOrUnavailable = (v: unknown): string => {
    if (typeof v === "number" && Number.isFinite(v)) {
      return v <= 1 ? `${Math.round(v * 100)}%` : String(v);
    }
    if (typeof v === "string" && v.trim()) return v;
    return DATA_UNAVAILABLE;
  };

  return {
    symbol: symbol.toUpperCase(),
    overallAccuracy: numOrUnavailable(dash?.overall_accuracy),
    recommendationAccuracy: numOrUnavailable(dash?.recommendation_accuracy),
    calibrationStatus:
      typeof drift?.status === "string"
        ? drift.status
        : DATA_UNAVAILABLE,
    timelineCount:
      typeof timeline?.total === "number"
        ? String(timeline.total)
        : Array.isArray(timeline?.timeline)
          ? String(timeline.timeline.length)
          : DATA_UNAVAILABLE,
    freshness: DATA_UNAVAILABLE,
    coverage:
      coverage && typeof coverage.snapshot_count === "number"
        ? `${coverage.snapshot_count} snapshots`
        : COVERAGE_UNAVAILABLE,
    source:
      dash || cal || timeline
        ? "research_intelligence"
        : "unavailable",
  };
}

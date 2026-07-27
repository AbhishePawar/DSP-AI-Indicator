/**
 * Deterministic comparison of two CopilotCompanyContext objects.
 * Only compares fields present on both sides — never estimates missing values.
 */

import { formatPct, formatScore } from "@/lib/intelligence/mapResponse";
import { UNAVAILABLE_ANSWER } from "./questions";
import type {
  CopilotCompanyContext,
  CopilotComposedAnswer,
  StageFieldSummary,
} from "./types";

function present(value: unknown): boolean {
  if (value == null) return false;
  if (typeof value === "string") {
    const v = value.trim().toLowerCase();
    return v !== "" && v !== "—" && v !== "unavailable";
  }
  return true;
}

function stageLine(
  label: string,
  a: StageFieldSummary,
  b: StageFieldSummary,
): string | null {
  if (!a.available || !b.available) return null;
  const left =
    a.label ||
    a.decision ||
    (a.score != null ? formatScore(a.score) : null) ||
    a.status;
  const right =
    b.label ||
    b.decision ||
    (b.score != null ? formatScore(b.score) : null) ||
    b.status;
  if (!present(left) || !present(right)) return null;
  return `• ${label}: ${left} vs ${right}`;
}

export function compareCompanyContexts(
  primary: CopilotCompanyContext | null,
  secondary: CopilotCompanyContext | null,
): CopilotComposedAnswer {
  if (!primary || !secondary) {
    return {
      content: `${UNAVAILABLE_ANSWER} Comparison requires two analysed companies in the current session. Run analysis for a second ticker, then ask again.`,
      citations: ["Overview"],
      intent: "compare_companies",
      unavailable: true,
    };
  }

  if (primary.ticker === secondary.ticker) {
    return {
      content: `${UNAVAILABLE_ANSWER} Both sides resolve to the same ticker (${primary.ticker}). Analyse a different company to compare.`,
      citations: ["Overview"],
      intent: "compare_companies",
      unavailable: true,
    };
  }

  const lines: string[] = [
    `Deterministic comparison of present fields only:`,
    `${primary.company} (${primary.ticker}) vs ${secondary.company} (${secondary.ticker})`,
  ];

  if (present(primary.recommendation) && present(secondary.recommendation)) {
    lines.push(
      `• Recommendation: ${primary.recommendation} vs ${secondary.recommendation}`,
    );
  }
  if (primary.marginOfSafety != null && secondary.marginOfSafety != null) {
    lines.push(
      `• Margin of safety: ${formatPct(primary.marginOfSafety)} vs ${formatPct(secondary.marginOfSafety)}`,
    );
  }
  if (primary.intrinsicValue != null && secondary.intrinsicValue != null) {
    lines.push(
      `• Intrinsic value (request signals): ${primary.intrinsicValue} vs ${secondary.intrinsicValue}`,
    );
  }
  if (
    present(primary.businessQualityLabel) &&
    present(secondary.businessQualityLabel)
  ) {
    lines.push(
      `• Business quality: ${primary.businessQualityLabel} vs ${secondary.businessQualityLabel}`,
    );
  }
  if (
    present(primary.committeeDecision) &&
    present(secondary.committeeDecision)
  ) {
    lines.push(
      `• Committee: ${primary.committeeDecision} vs ${secondary.committeeDecision}`,
    );
  }

  const stageLines = [
    stageLine("Economic moat", primary.economicMoat, secondary.economicMoat),
    stageLine(
      "Management quality",
      primary.managementQuality,
      secondary.managementQuality,
    ),
    stageLine(
      "Financial strength",
      primary.financialStrength,
      secondary.financialStrength,
    ),
    stageLine(
      "Earnings quality",
      primary.earningsQuality,
      secondary.earningsQuality,
    ),
    stageLine("Growth quality", primary.growthQuality, secondary.growthQuality),
  ].filter(Boolean) as string[];

  lines.push(...stageLines);

  const comparedFieldCount = lines.length - 2;
  if (comparedFieldCount <= 0) {
    return {
      content: `${UNAVAILABLE_ANSWER} The two analysed companies do not share enough overlapping present fields for a deterministic comparison.`,
      citations: ["Overview"],
      intent: "compare_companies",
      unavailable: true,
    };
  }

  lines.push(
    "Missing fields on either side were omitted rather than estimated.",
  );

  return {
    content: lines.join("\n"),
    citations: [
      "Recommendation",
      "Valuation",
      "Economic Moat",
      "Management Quality",
      "Financial Strength",
      "Earnings Quality",
      "Growth Quality",
      "Investment Committee",
      "Overview",
    ],
    intent: "compare_companies",
    unavailable: false,
  };
}

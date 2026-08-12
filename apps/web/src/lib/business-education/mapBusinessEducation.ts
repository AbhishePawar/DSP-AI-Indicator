/**
 * ARCH — Business & Buffett Educational Analysis mapper.
 *
 * Presentation synthesis only:
 * - No pipeline / package / engine recalculation
 * - Does not write intrinsic value, MoS, Buffett score, or recommendations
 * - Missing fields → "Data unavailable."
 */

import type { ResearchView, StageSectionView } from "@/lib/research/mapResearchView";
import {
  detectBusinessType,
  economicsFocus,
  preferredMetrics,
  type BusinessType,
} from "./businessTypes";
import type {
  BusinessEducationClaim,
  BusinessEducationReportView,
  BusinessEducationSectionView,
  BuffettChecklistItem,
  ClaimKind,
  KeyRiskItem,
} from "./types";

const UNAVAILABLE = "Data unavailable.";

const DISCLAIMER =
  "Business & Buffett Analysis is an educational business-understanding layer. It does not calculate intrinsic value, margin of safety, Buffett scores, or investment recommendations. Quantitative valuation remains authoritative in the valuation and Buffett Indicator engines. Research Mode — not investment advice.";

const SECTION_META: Array<{ id: string; title: string }> = [
  { id: "the_business_simply", title: "The Business, Simply" },
  { id: "how_the_economics_work", title: "How the Economics Work" },
  { id: "the_real_strengths", title: "The Real Strengths" },
  { id: "the_real_weaknesses", title: "The Real Weaknesses" },
  { id: "financial_health", title: "Financial Health" },
  { id: "key_risks_to_understand", title: "Key Risks to Understand" },
  { id: "the_buffett_checklist", title: "The Buffett Checklist" },
  {
    id: "management_and_capital_allocation",
    title: "Management & Capital Allocation",
  },
  { id: "the_behavioral_lens", title: "The Behavioral Lens" },
  {
    id: "what_would_change_the_thesis",
    title: "What Would Change the Thesis?",
  },
  {
    id: "data_quality_and_uncertainty",
    title: "Data Quality & Uncertainty",
  },
  { id: "educational_conclusion", title: "Educational Conclusion" },
];

const PROHIBITED =
  /\b(strong\s+buy|strong\s+sell|price\s+target|target\s+price|expected\s+return|future\s+price|\bbuy\b|\bsell\b|\bhold\b)\b/gi;

function isUnavailable(value: string | null | undefined): boolean {
  if (value == null) return true;
  const v = value.trim().toLowerCase();
  return (
    v === "" ||
    v === "unavailable" ||
    v === "data unavailable." ||
    v === "—" ||
    v === "n/a"
  );
}

function stageAvailable(section: StageSectionView): boolean {
  return (
    section.status === "succeeded" &&
    !isUnavailable(section.score) &&
    section.score.toLowerCase() !== "data unavailable."
  );
}

function metricValue(section: StageSectionView, label: string): string {
  const hit = section.metrics.find(
    (m) => m.label.toLowerCase() === label.toLowerCase(),
  );
  return hit?.value ?? UNAVAILABLE;
}

function claim(
  text: string,
  kind: ClaimKind,
  source: string | null,
  available = true,
): BusinessEducationClaim {
  return {
    text: available && text.trim() ? text : UNAVAILABLE,
    kind: available && text.trim() ? kind : "UNAVAILABLE",
    source,
    available: available && Boolean(text.trim()),
  };
}

function scrubVerdictLanguage(text: string): string {
  return text.replace(PROHIBITED, "educational summary");
}

function section(
  id: string,
  title: string,
  summary: string,
  claims: BusinessEducationClaim[],
  bullets: string[],
  extras?: Partial<BusinessEducationSectionView>,
): BusinessEducationSectionView {
  return {
    id,
    title,
    summary,
    claims,
    bullets,
    ...extras,
  };
}

type DraftView = Omit<
  ResearchView,
  | "buffett"
  | "businessEducation"
  | "ratings"
  | "transparency"
  | "explainability"
  | "valuationTransparency"
>;

export function mapBusinessEducation(view: DraftView): BusinessEducationReportView {
  const blob = `${view.company} ${view.ticker}`;
  const businessType: BusinessType = detectBusinessType(blob);
  const metrics = preferredMetrics(businessType);

  const moat = view.moat;
  const mgmt = view.management;
  const strength = view.financialStrength;
  const earnings = view.earnings;
  const growth = view.growth;
  const financial = view.financial;
  const bq = view.businessQuality;

  const warnings = [
    ...view.risks.slice(0, 8),
    ...view.weaknesses.slice(0, 4),
  ];

  const sections: BusinessEducationSectionView[] = [];

  // 1
  sections.push(
    section(
      SECTION_META[0].id,
      SECTION_META[0].title,
      `Beginner view of ${isUnavailable(view.company) ? "the company" : view.company}: how customers pay, drawn only from available stage evidence.`,
      [
        claim(
          `${view.company} (${view.ticker}) on ${view.exchange}.`,
          "FACT",
          "request_identity",
          !isUnavailable(view.company),
        ),
        claim(
          `Financial stage summary: ${financial.label}.`,
          "INTERPRETATION",
          "stage:financial",
          stageAvailable(financial),
        ),
        claim(
          "Detailed product/service catalogue is not exposed on AnalyseResponse — not invented.",
          "INTERPRETATION",
          "educational_layer",
        ),
      ],
      [
        `Business type lens: ${businessType}`,
        `Financial analysis: ${stageAvailable(financial) ? "available" : UNAVAILABLE}`,
      ],
    ),
  );

  // 2
  const econ = economicsFocus(businessType);
  sections.push(
    section(
      SECTION_META[1].id,
      SECTION_META[1].title,
      `Economics framing for business type '${businessType}'. Metrics shown only when present on stages.`,
      [
        ...econ.map((b) => claim(b, "INTERPRETATION", `business_type:${businessType}`)),
        claim(
          `Revenue Growth (stage): ${metricValue(growth, "Revenue Growth")}`,
          "CALCULATED_METRIC",
          "stage:growth_quality",
          !isUnavailable(metricValue(growth, "Revenue Growth")),
        ),
      ],
      [...econ, `Preferred metrics: ${metrics.join(", ")}`],
      { businessType, preferredMetrics: metrics },
    ),
  );

  // 3
  const strengthClaims: BusinessEducationClaim[] = stageAvailable(moat)
    ? [
        claim(
          `Moat label: ${moat.label}; decision: ${moat.decision}.`,
          "INTERPRETATION",
          "stage:economic_moat",
        ),
        claim(
          `Moat score (existing): ${moat.score}.`,
          "CALCULATED_METRIC",
          "stage:economic_moat",
          !isUnavailable(moat.score),
        ),
      ]
    : [claim(UNAVAILABLE, "UNAVAILABLE", "stage:economic_moat", false)];
  if (stageAvailable(bq)) {
    strengthClaims.push(
      claim(`Business quality: ${bq.label}.`, "INTERPRETATION", "stage:business_quality"),
    );
  }
  sections.push(
    section(
      SECTION_META[2].id,
      SECTION_META[2].title,
      "Strengths drawn from existing moat / quality / growth stages only.",
      strengthClaims,
      strengthClaims.filter((c) => c.available).map((c) => c.text),
    ),
  );

  // 4
  const weakClaims =
    warnings.length > 0
      ? warnings.map((w) => claim(w, "FACT", "stage_summaries.warnings"))
      : [
          claim(
            "No stage warnings available to evidence specific weaknesses.",
            "UNAVAILABLE",
            null,
            false,
          ),
        ];
  weakClaims.push(
    claim(
      "What could make the thesis wrong: deterioration in moat, financial strength, earnings, or growth stages.",
      "INTERPRETATION",
      "educational_layer",
    ),
  );
  sections.push(
    section(
      SECTION_META[3].id,
      SECTION_META[3].title,
      "Weaknesses listed only when evidenced by stage warnings or failures.",
      weakClaims,
      weakClaims.filter((c) => c.available).map((c) => c.text).slice(0, 10),
    ),
  );

  // 5
  const fhLabels: Array<[StageSectionView, string]> = [
    [growth, "Revenue Growth"],
    [growth, "Profit Growth"],
    [earnings, "Consistency"],
    [earnings, "Cash Conversion"],
    [strength, "Debt"],
    [strength, "Liquidity"],
    [strength, "Cash Flow"],
  ];
  const fhClaims = fhLabels.map(([stg, label]) => {
    const v = metricValue(stg, label);
    return claim(
      `${label}: ${v}`,
      "CALCULATED_METRIC",
      "stage_metrics",
      !isUnavailable(v),
    );
  });
  for (const m of metrics) {
    fhClaims.push(
      claim(`${m}: ${UNAVAILABLE}`, "UNAVAILABLE", `business_type:${businessType}`, false),
    );
  }
  sections.push(
    section(
      SECTION_META[4].id,
      SECTION_META[4].title,
      "Financial health uses stage fields only; missing values are Data unavailable.",
      fhClaims,
      fhClaims.map((c) => c.text).slice(0, 16),
      { preferredMetrics: metrics, businessType },
    ),
  );

  // 6
  const riskSeeds = warnings.slice(0, 3);
  const monitors = [
    "economic_moat.score / label",
    "financial_strength Debt / Liquidity / Cash Flow",
    "earnings_quality Consistency / Cash Conversion",
  ];
  const placeholders = [
    "Competitive / moat erosion (monitor economic_moat stage)",
    "Balance-sheet or liquidity stress (monitor financial_strength)",
    "Earnings quality deterioration (monitor earnings_quality)",
  ];
  const risks: KeyRiskItem[] = [0, 1, 2].map((i) => {
    const evidenced = i < riskSeeds.length;
    return {
      risk: evidenced ? riskSeeds[i]! : placeholders[i]!,
      whyItMatters: evidenced
        ? "Material to long-term business durability and capital outcomes."
        : "Educational monitoring lens when specific warnings are sparse.",
      potentialTrigger:
        "Adverse change in the related stage label, score, or warning.",
      metricToMonitor: monitors[i]!,
      kind: evidenced ? "FACT" : "INTERPRETATION",
      source: evidenced ? "stage_summaries.warnings" : "educational_layer",
    };
  });
  sections.push(
    section(
      SECTION_META[5].id,
      SECTION_META[5].title,
      "Three monitoring risks grounded in stage evidence when available.",
      risks.map((r) =>
        claim(`${r.risk} — monitor ${r.metricToMonitor}`, r.kind, r.source),
      ),
      risks.map((r) => r.risk),
      { risks },
    ),
  );

  // 7 checklist
  const checklistDefs: Array<[string, string, StageSectionView, string]> = [
    ["A", "Durable Competitive Moat", moat, "economic_moat"],
    ["B", "Manageable Debt / Financial Strength", strength, "financial_strength"],
    ["C", "Consistent Earnings", earnings, "earnings_quality"],
    ["D", "Pricing Power", moat, "economic_moat"],
    ["E", "Capable Management", mgmt, "management_quality"],
    ["F", "High Return on Capital", bq, "business_quality"],
    ["G", "Predictable Cash Generation", earnings, "earnings_quality"],
    ["H", "Rational Capital Allocation", mgmt, "management_quality"],
    ["I", "Long-Term Growth Runway", growth, "growth_quality"],
  ];
  const checklist: BuffettChecklistItem[] = checklistDefs.map(
    ([id, title, stg, src]) => {
      const available = stageAvailable(stg);
      return {
        id,
        title,
        evidence: available
          ? `label=${stg.label}; score=${stg.score}; decision=${stg.decision}`
          : UNAVAILABLE,
        strengthOrWeakness: available
          ? `Stage available (${stg.label}). Educational only — not a Buffett score.`
          : "Evidence unavailable from stage summary.",
        uncertainty: `Stage confidence: ${isUnavailable(stg.confidence) ? UNAVAILABLE : stg.confidence}`,
        source: `stage:${src}`,
      };
    },
  );
  sections.push(
    section(
      SECTION_META[6].id,
      SECTION_META[6].title,
      "Educational checklist mapped from existing stages. Does not replace the Buffett Indicator engine.",
      checklist.map((item) =>
        claim(
          `${item.id}. ${item.title}: ${item.strengthOrWeakness}`,
          item.evidence === UNAVAILABLE ? "UNAVAILABLE" : "INTERPRETATION",
          item.source,
          item.evidence !== UNAVAILABLE,
        ),
      ),
      checklist.map((i) => `${i.id}. ${i.title}`),
      { checklist },
    ),
  );

  // 8
  sections.push(
    section(
      SECTION_META[7].id,
      SECTION_META[7].title,
      "Management & capital allocation from management_quality / growth stages only.",
      [
        claim(
          `Management label: ${mgmt.label}.`,
          "INTERPRETATION",
          "stage:management_quality",
          stageAvailable(mgmt),
        ),
        claim(
          `Capital allocation field: ${metricValue(mgmt, "Capital Allocation")}`,
          "CALCULATED_METRIC",
          "stage:management_quality",
          !isUnavailable(metricValue(mgmt, "Capital Allocation")),
        ),
        claim(
          "Promoter ownership, buybacks, and related-party detail are not invented when absent.",
          "INTERPRETATION",
          "educational_layer",
        ),
        claim(
          "Management quality is not inferred from share-price performance.",
          "INTERPRETATION",
          "educational_layer",
        ),
      ],
      [
        `Management: ${stageAvailable(mgmt) ? mgmt.label : UNAVAILABLE}`,
        `Reinvestment: ${metricValue(growth, "Reinvestment")}`,
      ],
    ),
  );

  // 9
  const behavioral = [
    "THESIS → EVIDENCE → RISKS → VALUATION — not story → emotion → price chasing.",
    "Familiar brands, AI narratives, recent returns, or 'multibagger' talk can distort judgment.",
    "Low nominal share price or recent corrections can create false affordability/FOMO cues.",
    "Use this educational layer before interpreting quantitative valuation cards.",
  ];
  sections.push(
    section(
      SECTION_META[8].id,
      SECTION_META[8].title,
      "Why retail investors may become emotionally attracted — and how that distorts judgment.",
      behavioral.map((b) => claim(b, "INTERPRETATION", "educational_layer")),
      behavioral,
    ),
  );

  // 10
  const thesis = [
    `Strengthen: sustained improvement in moat/quality (moat: ${isUnavailable(moat.label) ? UNAVAILABLE : moat.label}).`,
    `Weaken: deterioration in financial strength or earnings (strength: ${isUnavailable(strength.label) ? UNAVAILABLE : strength.label}).`,
    `Monitor: ${metrics.slice(0, 6).join(", ")}.`,
    "Reassess when stage statuses flip to failed/unavailable or new material warnings appear.",
    "This section does not predict stock price.",
  ];
  sections.push(
    section(
      SECTION_META[9].id,
      SECTION_META[9].title,
      "Business-thesis monitors — not price forecasts.",
      thesis.map((b) => claim(b, "INTERPRETATION", "educational_layer")),
      thesis,
    ),
  );

  // 11
  const dq = [
    `Business type classification: ${businessType}.`,
    "Claim kinds: FACT, CALCULATED_METRIC, INTERPRETATION, MANAGEMENT_CLAIM, UNAVAILABLE.",
    "Missing fields display: Data unavailable.",
    "No fabricated citations or silent demo substitution.",
    "This layer cannot modify valuation or Buffett Indicator outputs.",
  ];
  sections.push(
    section(
      SECTION_META[10].id,
      SECTION_META[10].title,
      "Uncertainty is explicit; unavailable data is never filled with guesses.",
      dq.map((b) => claim(b, "INTERPRETATION", "provenance_guard")),
      dq,
    ),
  );

  // 12
  const conclusionRaw = [
    `What the business appears to do well (stage-backed): moat=${isUnavailable(moat.label) ? UNAVAILABLE : moat.label}; management=${isUnavailable(mgmt.label) ? UNAVAILABLE : mgmt.label}.`,
    `What makes it interesting to study: growth=${isUnavailable(growth.label) ? UNAVAILABLE : growth.label}; quality=${isUnavailable(bq.label) ? UNAVAILABLE : bq.label}.`,
    "Investors may underestimate: risks evidenced in stage warnings and balance-sheet fields.",
    "Investors may overestimate: narrative strength when stage evidence is thin or unavailable.",
    `Monitor: ${metrics.slice(0, 6).join(", ")} and the three key risks above.`,
    "This conclusion is educational only and is not an investment verdict.",
  ].join(" ");
  const conclusion = scrubVerdictLanguage(conclusionRaw);
  sections.push(
    section(
      SECTION_META[11].id,
      SECTION_META[11].title,
      conclusion,
      [claim(conclusion, "INTERPRETATION", "educational_layer")],
      [conclusion],
    ),
  );

  return {
    title: "Business & Buffett Analysis",
    disclaimer: DISCLAIMER,
    symbol: view.ticker,
    company: view.company,
    exchange: view.exchange,
    businessType,
    preferredMetrics: metrics,
    sections,
    readOnly: true,
    writesValuation: false,
    writesBuffettScore: false,
  };
}

/** Test helper — ensure conclusion has no investment verdict language. */
export function conclusionHasProhibitedVerdict(text: string): boolean {
  PROHIBITED.lastIndex = 0;
  return PROHIBITED.test(text);
}

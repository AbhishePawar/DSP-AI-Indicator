/**
 * Figma `ClientProfile.tsx` view-model.
 *
 * Form field registry (exact Figma labels/sections/hints), gauge geometry
 * (semicircle, 5 zones, needle) and payload mapping for
 * `GET/PUT /api/v1/workspace/profile`. The Financial Health Score, its
 * five components, zone and insight are computed by the server
 * (`compute_financial_health`) — nothing is scored in the browser.
 */

import type { FinancialHealthResult, FinancialProfilePayload } from "@/lib/api/workspaceTypes";

export type ProfileFieldKey =
  | "full_name"
  | "email"
  | "mobile"
  | "age"
  | "city"
  | "occupation"
  | "dependents"
  | "monthly_income"
  | "monthly_expenses"
  | "monthly_emi"
  | "other_monthly_income"
  | "total_savings"
  | "total_investments"
  | "emergency_fund"
  | "outstanding_loans"
  | "credit_card_outstanding"
  | "health_insurance"
  | "life_insurance"
  | "target_amount"
  | "target_year";

export type ProfileField = {
  key: ProfileFieldKey;
  label: string;
  kind: "text" | "int" | "money";
  placeholder?: string;
  hint?: string;
  locked?: boolean;
  optional?: boolean;
};

export type ProfileSection = { title: string; fields: readonly ProfileField[] };

/** Figma SectionCards 1–4 (+ goal fields in section 5). */
export const PROFILE_SECTIONS: readonly ProfileSection[] = [
  {
    title: "Personal Information",
    fields: [
      { key: "full_name", label: "Full Name", kind: "text", locked: true },
      { key: "email", label: "Email Address", kind: "text", locked: true },
      { key: "mobile", label: "Mobile Number", kind: "text", locked: true },
      { key: "age", label: "Age", kind: "int", placeholder: "28" },
      { key: "city", label: "City", kind: "text", placeholder: "Mumbai" },
      { key: "occupation", label: "Occupation", kind: "text", placeholder: "Salaried" },
      { key: "dependents", label: "No. of Dependents", kind: "int", placeholder: "2" },
    ],
  },
  {
    title: "Monthly Cash Flow",
    fields: [
      { key: "monthly_income", label: "Monthly Income", kind: "money", placeholder: "75,000", hint: "Your primary take-home income" },
      { key: "monthly_expenses", label: "Monthly Expenses", kind: "money", placeholder: "32,000", hint: "Household & living costs" },
      { key: "monthly_emi", label: "Monthly EMI / Debt", kind: "money", placeholder: "12,000" },
      { key: "other_monthly_income", label: "Other Monthly Income", kind: "money", placeholder: "0", optional: true },
    ],
  },
  {
    title: "Savings & Investments",
    fields: [
      { key: "total_savings", label: "Total Savings / Cash", kind: "money", placeholder: "4,50,000" },
      { key: "total_investments", label: "Total Investments", kind: "money", placeholder: "25,00,000", hint: "Stocks, MF, FD combined" },
      { key: "emergency_fund", label: "Emergency Fund", kind: "money", placeholder: "2,00,000" },
    ],
  },
  {
    title: "Debt & Protection",
    fields: [
      { key: "outstanding_loans", label: "Outstanding Loans", kind: "money", placeholder: "8,50,000" },
      { key: "credit_card_outstanding", label: "Credit Card Outstanding", kind: "money", placeholder: "0" },
      { key: "health_insurance", label: "Health Insurance", kind: "money", placeholder: "10,00,000" },
      { key: "life_insurance", label: "Life / Term Insurance", kind: "money", placeholder: "50,00,000" },
    ],
  },
];

export const GOAL_FIELDS: readonly ProfileField[] = [
  { key: "target_amount", label: "Target Amount", kind: "money", placeholder: "2,00,00,000", optional: true },
  { key: "target_year", label: "Target Year", kind: "int", placeholder: "2036", optional: true },
];

/** Figma GOALS — ids are the server `primary_goal` enum. */
export const PROFILE_GOALS = [
  { id: "wealth_creation", label: "Wealth Creation", icon: "📈" },
  { id: "retirement", label: "Retirement", icon: "🏖️" },
  { id: "regular_income", label: "Regular Income", icon: "💰" },
  { id: "childrens_education", label: "Children's Education", icon: "🎓" },
  { id: "home_purchase", label: "Home Purchase", icon: "🏠" },
  { id: "marriage", label: "Marriage", icon: "💍" },
  { id: "emergency_fund", label: "Emergency Fund", icon: "🛡️" },
  { id: "other", label: "Other", icon: "✦" },
] as const;

export type ProfileGoalId = (typeof PROFILE_GOALS)[number]["id"];

export type InvestmentRow = { label: string; kind: string; amount: string };

export type ProfileFormState = {
  values: Record<ProfileFieldKey, string>;
  noOutstandingDebt: boolean;
  primaryGoal: ProfileGoalId | null;
  investments: InvestmentRow[];
};

const ALL_FIELDS: readonly ProfileField[] = [...PROFILE_SECTIONS.flatMap((s) => s.fields), ...GOAL_FIELDS];

/** Indian grouping (12,34,567) for display of stored numbers. */
export function formatInrInput(value: number): string {
  return Math.round(value).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

/** "4,50,000" / "₹ 4,50,000" → 450000; empty → null; garbage → NaN. */
export function parseInrInput(raw: string): number | null {
  const cleaned = raw.replace(/[₹,\s]/g, "");
  if (!cleaned) return null;
  return Number(cleaned);
}

export function emptyProfileForm(): ProfileFormState {
  const values = {} as Record<ProfileFieldKey, string>;
  for (const f of ALL_FIELDS) values[f.key] = "";
  return { values, noOutstandingDebt: false, primaryGoal: null, investments: [] };
}

/** Server profile → form strings (money fields shown with Indian grouping). */
export function profileToForm(profile: FinancialProfilePayload | null | undefined): ProfileFormState {
  const form = emptyProfileForm();
  if (!profile) return form;
  for (const f of ALL_FIELDS) {
    const raw = profile[f.key];
    if (raw === null || raw === undefined || raw === "") continue;
    form.values[f.key] =
      f.kind === "money" && typeof raw === "number" ? formatInrInput(raw) : String(raw);
  }
  form.noOutstandingDebt = Boolean(profile.no_outstanding_debt);
  const goal = typeof profile.primary_goal === "string" ? profile.primary_goal : null;
  form.primaryGoal = PROFILE_GOALS.some((g) => g.id === goal) ? (goal as ProfileGoalId) : null;
  const inv = Array.isArray(profile.investments) ? profile.investments : [];
  form.investments = inv.map((item) => {
    const row = (item ?? {}) as Record<string, unknown>;
    return {
      label: typeof row.label === "string" ? row.label : "",
      kind: typeof row.kind === "string" ? row.kind : "",
      amount: typeof row.amount === "number" ? formatInrInput(row.amount) : "",
    };
  });
  return form;
}

export type FormToPayloadResult =
  | { ok: true; payload: FinancialProfilePayload }
  | { ok: false; errors: Partial<Record<ProfileFieldKey, string>> };

/** Form strings → server payload; locked fields are never sent. */
export function formToPayload(form: ProfileFormState): FormToPayloadResult {
  const payload: FinancialProfilePayload = {};
  const errors: Partial<Record<ProfileFieldKey, string>> = {};
  for (const f of ALL_FIELDS) {
    if (f.locked) continue;
    const raw = form.values[f.key]?.trim() ?? "";
    if (!raw) {
      payload[f.key] = null;
      continue;
    }
    if (f.kind === "text") {
      payload[f.key] = raw;
    } else if (f.kind === "int") {
      const n = Number(raw);
      if (!Number.isInteger(n) || n < 0) errors[f.key] = "Enter a whole number.";
      else payload[f.key] = n;
    } else {
      const n = parseInrInput(raw);
      if (n === null || !Number.isFinite(n) || n < 0) errors[f.key] = "Enter an amount in ₹.";
      else payload[f.key] = n;
    }
  }
  payload.no_outstanding_debt = form.noOutstandingDebt;
  payload.primary_goal = form.primaryGoal;
  payload.investments = form.investments
    .filter((r) => r.label.trim() || r.amount.trim())
    .map((r) => ({
      label: r.label.trim(),
      kind: r.kind.trim() || null,
      amount: parseInrInput(r.amount) ?? null,
    }));
  if (Object.keys(errors).length) return { ok: false, errors };
  return { ok: true, payload };
}

// ── Gauge geometry (Figma HealthGauge: cx 160, cy 130, r 110) ────────────────

export const GAUGE = { cx: 160, cy: 130, r: 110, width: 320, height: 170 } as const;

/** Figma zones, left (180°) → right (0°). */
export const GAUGE_ZONES = [
  { start: 180, end: 144, color: "#ef4444", label: "Very Poor", labelDeg: 162 },
  { start: 144, end: 108, color: "#f97316", label: "Poor", labelDeg: 126 },
  { start: 108, end: 72, color: "#f59e0b", label: "Fair", labelDeg: 90 },
  { start: 72, end: 36, color: "#22c55e", label: "Good", labelDeg: 54 },
  { start: 36, end: 0, color: "#10b981", label: "Excellent", labelDeg: 18 },
] as const;

const toRad = (d: number) => (d * Math.PI) / 180;

export function gaugeArcPath(startDeg: number, endDeg: number, ri = 80, ro = 110): string {
  const { cx, cy } = GAUGE;
  const s = toRad(startDeg);
  const e = toRad(endDeg);
  const x1o = cx + ro * Math.cos(s);
  const y1o = cy - ro * Math.sin(s);
  const x2o = cx + ro * Math.cos(e);
  const y2o = cy - ro * Math.sin(e);
  const x1i = cx + ri * Math.cos(s);
  const y1i = cy - ri * Math.sin(s);
  const x2i = cx + ri * Math.cos(e);
  const y2i = cy - ri * Math.sin(e);
  const large = Math.abs(startDeg - endDeg) > 180 ? 1 : 0;
  return `M${x1o},${y1o} A${ro},${ro} 0 ${large},0 ${x2o},${y2o} L${x2i},${y2i} A${ri},${ri} 0 ${large},1 ${x1i},${y1i} Z`;
}

export function gaugePoint(deg: number, radius: number): { x: number; y: number } {
  return { x: GAUGE.cx + radius * Math.cos(toRad(deg)), y: GAUGE.cy - radius * Math.sin(toRad(deg)) };
}

/** Needle tip for a 0–1000 score (180° = 0, 0° = 1000). */
export function gaugeNeedle(score: number): { x: number; y: number } {
  const pct = Math.min(Math.max(score / 1000, 0), 1);
  return gaugePoint(180 - pct * 180, GAUGE.r - 10);
}

/** Figma label colours per zone (server decides the category). */
export function zoneColor(category: string | null | undefined): string {
  switch (category) {
    case "Excellent":
      return "#10b981";
    case "Good":
      return "#22c55e";
    case "Fair":
      return "#f59e0b";
    case "Poor":
      return "#f97316";
    case "Very Poor":
      return "#ef4444";
    default:
      return "var(--muted)";
  }
}

/** Figma ScoreRow bar colour: ≥75 green · ≥55 amber · else red. */
export function scoreRowColor(value: number, max = 100): string {
  const pct = (value / max) * 100;
  return pct >= 75 ? "#22c55e" : pct >= 55 ? "#f59e0b" : "#ef4444";
}

/** Figma "What influences your score?" rows — server components, or placeholders. */
export const SCORE_ROW_LABELS = [
  "Income Strength",
  "Savings & Investments",
  "Debt Management",
  "Emergency Protection",
  "Goal Readiness",
] as const;

export function scoreRows(health: FinancialHealthResult | undefined): { label: string; value: number | null; max: number }[] {
  if (health?.status === "complete" && health.components.length) {
    return health.components.map((c) => ({ label: c.label, value: c.score, max: c.max }));
  }
  return SCORE_ROW_LABELS.map((label) => ({ label, value: null, max: 100 }));
}

/** Figma CTA copy toggles once a score exists. */
export function primaryCtaLabel(health: FinancialHealthResult | undefined): string {
  return health?.status === "complete" ? "Update Financial Profile" : "Calculate My Financial Health Score";
}

/** Human labels for `missing_inputs` keys (server) using the Figma field registry. */
export function fieldLabel(key: string): string {
  if (key === "primary_goal") return "Primary Financial Goal";
  return ALL_FIELDS.find((f) => f.key === key)?.label ?? key;
}

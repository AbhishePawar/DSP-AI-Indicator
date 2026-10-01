/**
 * Transport types for the Figma-first `/api/v1` contracts:
 * market indices · investor workspace (watchlist / portfolio / dashboard /
 * saved research / canvas / profile) · coverage registry (institutional /
 * directory / signals). Mirror server DTOs only — no client derivations.
 */

export type MarketIndexPayload = {
  index_id: string;
  label: string;
  exchange: string;
  currency: string;
  available: boolean;
  authenticated: boolean;
  value: number | null;
  change: number | null;
  change_percent: number | null;
  previous_close: number | null;
  sparkline: number[];
  as_of: string | null;
  provenance: Record<string, unknown> | null;
};

export type MarketIndicesResponse = {
  ok: boolean;
  available: boolean;
  authenticated: boolean;
  provider_id?: string | null;
  indices: MarketIndexPayload[];
  message?: string | null;
  capability?: string;
  error?: string;
};

export type WorkspaceQuote = {
  price: number | null;
  change: number | null;
  change_percent: number | null;
  previous_close: number | null;
  currency: string | null;
  provenance: Record<string, unknown> | null;
  available: boolean;
};

export type WatchlistItem = {
  symbol: string;
  exchange: string | null;
  company_name: string | null;
  sector: string | null;
  rating: string | null;
  business_quality_score: number | null;
  rated_at: string | null;
  quote: WorkspaceQuote;
  added_at: string | null;
  origin?: "watchlist" | "research";
};

export type WatchlistResponse = {
  ok: boolean;
  items: WatchlistItem[];
  count: number;
  removed?: boolean;
};

export type PortfolioHoldingRow = {
  holding_id: string;
  symbol: string;
  exchange: string | null;
  company_name: string | null;
  sector: string | null;
  rating: string | null;
  business_quality_score: number | null;
  quantity: number;
  average_cost: number;
  invested: number;
  cmp: number | null;
  current_value: number | null;
  pnl: number | null;
  return_pct: number | null;
  weight: number | null;
  quote: WorkspaceQuote;
  updated_at: string | null;
};

export type PortfolioSummary = {
  holdings: number;
  priced_holdings: number;
  complete: boolean;
  total_invested: number;
  current_value: number | null;
  total_pnl: number | null;
  return_pct: number | null;
  formula: Record<string, string>;
};

export type SectorAllocationRow = {
  sector: string | null;
  value: number;
  weight: number | null;
};

export type PortfolioResponse = {
  ok: boolean;
  summary: PortfolioSummary;
  holdings: PortfolioHoldingRow[];
  sector_allocation: SectorAllocationRow[];
  message: string | null;
  removed?: boolean;
  cleared?: number;
};

export type CoverageSignal = {
  signal_id: string;
  symbol: string;
  company_name: string | null;
  sector: string | null;
  timestamp: string;
  research_id: string | null;
  type: "upgrade" | "downgrade" | "risk" | "valuation";
  label: string;
  text: string;
  severity?: "info" | "warning" | "alert" | null;
  status?: string | null;
  source?: string | null;
  dsp_context?: Record<string, unknown> | null;
  from_rating?: string | null;
  to_rating?: string | null;
  from_value?: number | null;
  to_value?: number | null;
};

export type RecentResearchItem = {
  symbol: string;
  company_name: string | null;
  title?: string | null;
  rating: string | null;
  recommendation: string | null;
  tags?: string[];
  timestamp: string;
  research_id: string | null;
  href?: string | null;
};

export type DashboardOverviewResponse = {
  ok: boolean;
  watchlist: WatchlistItem[];
  recent_research: RecentResearchItem[];
  signals: CoverageSignal[];
};

export type SavedResearchItem = {
  saved_id: string;
  symbol: string;
  title: string;
  tags: string[];
  turns: number | null;
  research_id: string | null;
  created_at: string;
  updated_at: string;
};

export type CanvasBlockPayload = {
  id: string;
  type: "heading" | "text" | "metric" | "table" | "chart-ref" | "divider";
  content: string;
  meta: Record<string, unknown>;
};

export type CanvasItem = {
  canvas_id: string;
  title: string;
  blocks: CanvasBlockPayload[];
  version: number;
  created_at: string;
  updated_at: string;
};

export type FinancialHealthComponent = {
  key: string;
  label: string;
  score: number | null;
  max: number;
  formula: string;
  inputs: Record<string, unknown>;
  note: string;
};

export type FinancialHealthResult = {
  version: string;
  status: "complete" | "incomplete";
  score: number | null;
  max: number;
  category: string | null;
  components: FinancialHealthComponent[];
  insight: string;
  missing_inputs: string[];
  completeness: { percent: number; filled: number; total: number; missing: string[] };
  calculated_at?: string;
};

export type FinancialProfilePayload = Record<string, unknown>;

export type ProfileResponse = {
  ok: boolean;
  profile: FinancialProfilePayload | null;
  completeness: { percent: number; filled: number; total: number; missing: string[] };
  health: FinancialHealthResult;
};

export type CoverageStats = {
  securities_covered: number;
  dsp_rated: number;
  a_rated: number;
  a_plus_rated: number;
  last_updated: string | null;
};

export type ScreenerRow = {
  symbol: string;
  company_name: string | null;
  rating: string | null;
  business_quality_score: number | null;
  sector: string | null;
  pe: number | null;
  roe: number | null;
  roce?: number | null;
  revenue_growth: number | null;
  fcf?: number | null;
  price: number | null;
  market_cap: number | null;
  as_of: string;
  research_id: string | null;
};

export type InstitutionalResponse = {
  ok: boolean;
  stats: CoverageStats;
  screener: ScreenerRow[];
  coverage_growth: { month: string; period: string; covered: number; rated: number }[];
  rating_distribution: { rating: string; count: number }[];
  sectors: string[];
  message: string | null;
};

export type DirectoryItem = {
  symbol: string;
  company_name: string | null;
  exchange: string | null;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  rating: string | null;
  price: number | null;
  change?: number | null;
  change_percent?: number | null;
  as_of: string;
};

export type DirectoryResponse = {
  ok: boolean;
  items: DirectoryItem[];
  count: number;
  limit?: number;
  offset?: number;
  sectors: string[];
};

export type CompareResponse = {
  ok: boolean;
  available: boolean;
  a: Record<string, unknown> | null;
  b: Record<string, unknown> | null;
  metrics: { key: string; label: string; suffix: string; a: number | null; b: number | null; winner: string | null }[];
  radar: { a: Record<string, number | null>; b: Record<string, number | null> };
  formula: Record<string, string>;
  message: string | null;
};

export type SignalsResponse = {
  ok: boolean;
  signals: CoverageSignal[];
  today: {
    new_signals: number;
    upgrades: number;
    downgrades: number;
    risk_flags: number;
    as_of: string;
  };
  sectors: string[];
  count: number;
};

// ── Figma Control Center (user settings) ────────────────────────────────────

export type PreferenceKey =
  | "notifications"
  | "dsp_alerts"
  | "email_digest"
  | "peer_comparisons"
  | "auto_research"
  | "dark_mode"
  | "compact_view"
  | "beta_features";

export type Preferences = Record<PreferenceKey, boolean> & { updated_at?: string };

export type PreferencesResponse = { ok: boolean; preferences: Preferences };

// ── Figma Advisor (client book) ─────────────────────────────────────────────

export type AdvisorRiskProfile = "conservative" | "moderate" | "aggressive";

export type AdvisorClient = {
  client_id: string;
  name: string;
  email: string | null;
  risk_profile: AdvisorRiskProfile;
  /** Advisor-entered figure; null → "Data unavailable." */
  portfolio_value: number | null;
  notes: string | null;
  research_sessions: number;
  last_session_at?: string;
  created_at: string;
  updated_at: string;
};

export type AdvisorClientPayload = {
  name: string;
  risk_profile: AdvisorRiskProfile;
  email?: string | null;
  portfolio_value?: number | null;
  notes?: string | null;
};

export type AdvisorOverview = {
  active_clients: number;
  total_portfolio_value: number | null;
  clients_with_portfolio_value: number;
  research_sessions: number;
  risk_profile_counts: Record<AdvisorRiskProfile, number>;
};

export type AdvisorClientsResponse = {
  ok: boolean;
  items: AdvisorClient[];
  count: number;
  overview: AdvisorOverview;
};

// ── Figma Contact ───────────────────────────────────────────────────────────

export type ContactPayload = {
  name: string;
  email: string;
  message: string;
  source?: string;
};

export type ContactResponse = { ok: boolean; message_id: string; received_at: string };

// ── Figma Coupons & Offers (SaaS overlay coupon metadata) ───────────────────

export type CouponCategory = "premium" | "research" | "analysis" | "referral";
export type CouponDiscountType = "percent" | "flat" | "free";

export type Coupon = {
  code: string;
  discount_pct: number | null;
  active: boolean;
  expires_at: string | null;
  title: string | null;
  description: string | null;
  category: CouponCategory;
  discount_type: CouponDiscountType;
  discount_label: string | null;
  applicable_to: string[];
  min_spend: number | string | null;
  featured: boolean;
  created_at: string;
  updated_at: string;
  note?: string;
};

export type CouponsResponse = {
  ok: boolean;
  result?: { coupons: Coupon[] };
  message?: string | null;
  error?: string;
};

export type ReferralProgramme = {
  title: string | null;
  description: string | null;
  discount_pct: number | null;
  discount_label: string | null;
  coupon_code: string | null;
};

export type ReferralProfile = {
  code: string;
  path: string;
  referred_count: number;
  savings_status: "unavailable";
  programme: ReferralProgramme | null;
};

export type ReferralResponse = {
  ok: boolean;
  result?: { referral: ReferralProfile };
  message?: string | null;
  error?: string;
};

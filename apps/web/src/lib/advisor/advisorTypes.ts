/**
 * Epic V2.0 Sprint 1–2 — Advisor domain types (presentation only).
 * Isolated from Research / Portfolio / Compliance engines.
 */

export type AdvisorId = string;
export type OrganizationId = string;
export type ClientId = string;
export type MeetingId = string;
export type TaskId = string;
export type ModelPortfolioId = string;
export type ResearchCollectionId = string;
export type NoteId = string;
export type ResearchEventId = string;

export type RiskBand = "conservative" | "moderate" | "growth" | "aggressive";

export type ReviewStatus = "on_track" | "due_soon" | "overdue" | "completed";

export type PortfolioSizeBand = "small" | "medium" | "large" | "institutional";

export type ModelPortfolioStyle =
  | "growth"
  | "balanced"
  | "income"
  | "value"
  | "quality"
  | "custom";

export type TaskKind =
  | "upcoming_review"
  | "meeting_followup"
  | "research_request"
  | "portfolio_review";

export type TaskStatus = "todo" | "in_progress" | "waiting" | "done";

export type TaskPriority = "p0" | "p1" | "p2" | "p3";

export type MeetingStatus = "scheduled" | "completed" | "cancelled";

export type NoteKind = "pinned" | "meeting" | "research" | "advisor";

export type ResearchHistoryKind =
  | "company_reviewed"
  | "report_exported"
  | "portfolio_review"
  | "saved_research";

export type Organization = {
  id: OrganizationId;
  name: string;
  region: string;
  trustNote: string;
};

export type AdvisorProfile = {
  id: AdvisorId;
  displayName: string;
  title: string;
  organizationId: OrganizationId;
  specialties: string[];
};

export type ClientRelationship = {
  clientId: ClientId;
  advisorId: AdvisorId;
  since: string;
  role: "primary" | "secondary" | "coverage";
};

export type ClientSummary = {
  id: ClientId;
  /** Demo alias only — never real personal data */
  alias: string;
  segment: string;
  riskProfile: RiskBand;
  objectives: string[];
  lastTouchAt: string;
  portfolioSnapshotLabel: string;
  researchHistoryCount: number;
  reviewStatus: ReviewStatus;
  portfolioSizeBand: PortfolioSizeBand;
  /** Demo AUM band label — not real money */
  portfolioSizeLabel: string;
  meetingDueAt: string | null;
  nextReviewAt: string;
  portfolioHealthLabel: string;
};

export type Meeting = {
  id: MeetingId;
  clientId: ClientId | null;
  title: string;
  scheduledAt: string;
  status: MeetingStatus;
  agenda: string;
  notesPlaceholder: string;
  reviewNotes: string;
  actionItems: string[];
};

export type Task = {
  id: TaskId;
  title: string;
  kind: TaskKind;
  status: TaskStatus;
  priority: TaskPriority;
  dueAt: string;
  clientId: ClientId | null;
  /** Demo owner alias — not a real identity */
  owner: string;
};

export type ClientNote = {
  id: NoteId;
  clientId: ClientId;
  kind: NoteKind;
  title: string;
  body: string;
  pinned: boolean;
  updatedAt: string;
};

export type ResearchHistoryEvent = {
  id: ResearchEventId;
  clientId: ClientId;
  kind: ResearchHistoryKind;
  label: string;
  occurredAt: string;
};

export type AllocationSlice = {
  label: string;
  weightPct: number;
};

export type ModelPortfolio = {
  id: ModelPortfolioId;
  name: string;
  style: ModelPortfolioStyle;
  description: string;
  allocations: AllocationSlice[];
  demoOnly: true;
};

export type ResearchCollection = {
  id: ResearchCollectionId;
  name: string;
  kind: "folder" | "favorites" | "saved_companies" | "pinned";
  itemLabels: string[];
};

export type Advisor = {
  profile: AdvisorProfile;
  organization: Organization;
};

export type ClientDirectorySort =
  | "alias_asc"
  | "alias_desc"
  | "activity"
  | "meeting_due"
  | "risk"
  | "portfolio_size"
  | "review_status";

export type ClientDirectoryFilters = {
  query: string;
  riskProfile: RiskBand | "all";
  reviewStatus: ReviewStatus | "all";
  portfolioSize: PortfolioSizeBand | "all";
  sort: ClientDirectorySort;
};

/**
 * Advisor view-models — pure transforms over demo fixtures.
 */

import {
  demoAdvisor,
  demoClients,
  demoMeetings,
  demoModelPortfolios,
  demoNotes,
  demoResearchCollections,
  demoResearchHistory,
  demoTasks,
} from "./advisorModels";
import type {
  ClientNote,
  ClientSummary,
  Meeting,
  MeetingStatus,
  ModelPortfolio,
  ResearchCollection,
  ResearchHistoryEvent,
  Task,
  TaskKind,
  TaskStatus,
} from "./advisorTypes";

export type AdvisorOverviewView = {
  advisorName: string;
  organizationName: string;
  todaysMeetings: Meeting[];
  pendingTasks: Task[];
  recentResearch: string[];
  clientActivity: { alias: string; lastTouchAt: string; segment: string }[];
  portfolioReviews: Task[];
};

export type ClientDashboardView = {
  client: ClientSummary;
  portfolioHealth: string;
  meetingStatus: string;
  outstandingTasks: Task[];
  recentResearch: ResearchHistoryEvent[];
  riskLevel: string;
  nextReview: string;
};

export type ClientProfileView = {
  client: ClientSummary;
  dashboard: ClientDashboardView;
  objectives: string[];
  riskProfile: string;
  researchHistory: ResearchHistoryEvent[];
  portfolioSnapshot: string;
  meetings: Meeting[];
  tasks: Task[];
  notes: ClientNote[];
  documentsPlaceholder: string[];
  meetingNotes: string[];
};

export function buildAdvisorOverview(): AdvisorOverviewView {
  const todayPrefix = "2026-07-22";
  const todaysMeetings = demoMeetings.filter(
    (m) => m.status === "scheduled" && m.scheduledAt.startsWith(todayPrefix),
  );
  const pendingTasks = demoTasks.filter((t) => t.status !== "done");
  const recentResearch = demoResearchCollections.flatMap((c) => c.itemLabels).slice(0, 5);
  const clientActivity = [...demoClients]
    .sort((a, b) => b.lastTouchAt.localeCompare(a.lastTouchAt))
    .slice(0, 5)
    .map((c) => ({
      alias: c.alias,
      lastTouchAt: c.lastTouchAt,
      segment: c.segment,
    }));
  const portfolioReviews = demoTasks.filter((t) => t.kind === "portfolio_review");

  return {
    advisorName: demoAdvisor.profile.displayName,
    organizationName: demoAdvisor.organization.name,
    todaysMeetings,
    pendingTasks,
    recentResearch,
    clientActivity,
    portfolioReviews,
  };
}

export function buildClientDashboard(clientId: string): ClientDashboardView | null {
  const client = demoClients.find((c) => c.id === clientId);
  if (!client) return null;
  const outstandingTasks = demoTasks.filter(
    (t) => t.clientId === clientId && t.status !== "done",
  );
  const upcoming = demoMeetings.find(
    (m) => m.clientId === clientId && m.status === "scheduled",
  );
  const recentResearch = demoResearchHistory
    .filter((e) => e.clientId === clientId)
    .sort((a, b) => b.occurredAt.localeCompare(a.occurredAt))
    .slice(0, 4);

  return {
    client,
    portfolioHealth: client.portfolioHealthLabel,
    meetingStatus: upcoming
      ? `Upcoming · ${upcoming.title}`
      : client.reviewStatus === "overdue"
        ? "No upcoming meeting · review overdue"
        : "No upcoming meeting",
    outstandingTasks,
    recentResearch,
    riskLevel: client.riskProfile,
    nextReview: client.nextReviewAt,
  };
}

export function buildClientProfile(clientId: string): ClientProfileView | null {
  const client = demoClients.find((c) => c.id === clientId);
  if (!client) return null;
  const dashboard = buildClientDashboard(clientId);
  if (!dashboard) return null;
  const meetings = demoMeetings.filter((m) => m.clientId === clientId);
  const tasks = demoTasks.filter((t) => t.clientId === clientId);
  const notes = demoNotes
    .filter((n) => n.clientId === clientId)
    .sort((a, b) => Number(b.pinned) - Number(a.pinned) || b.updatedAt.localeCompare(a.updatedAt));
  const researchHistory = demoResearchHistory
    .filter((e) => e.clientId === clientId)
    .sort((a, b) => b.occurredAt.localeCompare(a.occurredAt));

  return {
    client,
    dashboard,
    objectives: client.objectives,
    riskProfile: client.riskProfile,
    researchHistory,
    portfolioSnapshot: client.portfolioSnapshotLabel,
    meetings,
    tasks,
    notes,
    documentsPlaceholder: [
      "KYC packet (placeholder)",
      "IPS summary (placeholder)",
      "Signed disclosures (placeholder)",
    ],
    meetingNotes: meetings.map((m) => `${m.title}: ${m.notesPlaceholder}`),
  };
}

export function listClients(): ClientSummary[] {
  return demoClients;
}

export function listMeetings(): Meeting[] {
  return demoMeetings;
}

export function listMeetingsByStatus(status: MeetingStatus): Meeting[] {
  return demoMeetings.filter((m) => m.status === status);
}

export function listTasks(): Task[] {
  return demoTasks;
}

export function listTasksByKind(kind: TaskKind): Task[] {
  return demoTasks.filter((t) => t.kind === kind);
}

export function listTasksByStatus(status: TaskStatus): Task[] {
  return demoTasks.filter((t) => t.status === status);
}

export function listModelPortfolios(): ModelPortfolio[] {
  return demoModelPortfolios;
}

export function listResearchCollections(): ResearchCollection[] {
  return demoResearchCollections;
}

export function listNotesForClient(clientId: string): ClientNote[] {
  return demoNotes.filter((n) => n.clientId === clientId);
}

export function listResearchHistoryForClient(clientId: string): ResearchHistoryEvent[] {
  return demoResearchHistory.filter((e) => e.clientId === clientId);
}

export function clientAlias(clientId: string | null): string {
  if (!clientId) return "Internal";
  return demoClients.find((c) => c.id === clientId)?.alias ?? "Unknown demo client";
}

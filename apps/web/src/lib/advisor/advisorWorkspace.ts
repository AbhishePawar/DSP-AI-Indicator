/**
 * Advisor workspace facade — demo-only composition root.
 * Advisor Layer → Presentation Layer → Existing Research Platform (no coupling).
 */

import { DEMO_TRUST_BANNER, demoAdvisor } from "./advisorModels";
import {
  buildAdvisorOverview,
  buildClientProfile,
  listClients,
  listMeetings,
  listModelPortfolios,
  listResearchCollections,
  listTasks,
  listTasksByKind,
  clientAlias,
} from "./advisorViewModel";

export type AdvisorSection =
  | "overview"
  | "clients"
  | "meetings"
  | "tasks"
  | "research"
  | "portfolios"
  | "presentations"
  | "reviews"
  | "team";

export const ADVISOR_SECTIONS: { id: AdvisorSection; href: string; label: string }[] = [
  { id: "overview", href: "/advisor", label: "Overview" },
  { id: "clients", href: "/advisor/clients", label: "Clients" },
  { id: "meetings", href: "/advisor/meetings", label: "Meetings" },
  { id: "tasks", href: "/advisor/tasks", label: "Tasks" },
  { id: "research", href: "/advisor/research", label: "Research" },
  { id: "portfolios", href: "/advisor/portfolios", label: "Model Portfolios" },
  { id: "presentations", href: "/advisor/presentations", label: "Presentations" },
  { id: "reviews", href: "/advisor/reviews", label: "Reviews" },
  { id: "team", href: "/advisor/team", label: "Team Collaboration" },
];

export function getAdvisorWorkspace() {
  return {
    trustBanner: DEMO_TRUST_BANNER,
    advisor: demoAdvisor,
    overview: buildAdvisorOverview(),
    clients: listClients(),
    meetings: listMeetings(),
    tasks: listTasks(),
    researchCollections: listResearchCollections(),
    modelPortfolios: listModelPortfolios(),
    sections: ADVISOR_SECTIONS,
    helpers: {
      buildClientProfile,
      listTasksByKind,
      clientAlias,
    },
  };
}

export type AdvisorWorkspaceSnapshot = ReturnType<typeof getAdvisorWorkspace>;

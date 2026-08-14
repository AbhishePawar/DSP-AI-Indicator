/**
 * EPIC-F008 — Administration Console section registry.
 */

export type AdminSectionId =
  | "overview"
  | "identity"
  | "audit"
  | "platform"
  | "metrics"
  | "workflow"
  | "research"
  | "export"
  | "beta";

export type AdminSectionMeta = {
  id: AdminSectionId;
  label: string;
  description: string;
  shortcut: string;
};

export const ADMIN_SECTIONS: readonly AdminSectionMeta[] = [
  {
    id: "overview",
    label: "Overview",
    description: "Administration dashboard",
    shortcut: "1",
  },
  {
    id: "identity",
    label: "Identity",
    description: "Users, roles, permissions, sessions",
    shortcut: "2",
  },
  {
    id: "audit",
    label: "Audit",
    description: "Audit log and activity timeline",
    shortcut: "3",
  },
  {
    id: "platform",
    label: "Platform",
    description: "Health, versions, configuration, flags",
    shortcut: "4",
  },
  {
    id: "metrics",
    label: "Metrics",
    description: "System metrics from A010",
    shortcut: "5",
  },
  {
    id: "workflow",
    label: "Workflow",
    description: "Workflow history and activity",
    shortcut: "6",
  },
  {
    id: "research",
    label: "Research refs",
    description: "Archive metadata references",
    shortcut: "7",
  },
  {
    id: "export",
    label: "Export",
    description: "Export audit metadata and snapshots",
    shortcut: "8",
  },
  {
    id: "beta",
    label: "Closed Beta",
    description: "Invites, feedback, analytics (P5.1)",
    shortcut: "9",
  },
] as const;

export function isAdminSectionId(value: string): value is AdminSectionId {
  return ADMIN_SECTIONS.some((s) => s.id === value);
}

export const ADMIN_ACCESS_PERMISSIONS = [
  "manage_users",
  "manage_roles",
  "configure_platform",
  "view_audit",
] as const;

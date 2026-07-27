/**
 * In-memory collaboration session state (no persistence).
 */

import {
  DEFAULT_COLLAB_SESSION,
  type CollaborationNavId,
  type CollaborationPanelId,
  type CollaborationSessionState,
  type CollaborationWorkspaceKind,
} from "./collaborationTypes";
import { COLLAB_NAV } from "./collaborationTypes";

let state: CollaborationSessionState = {
  ...DEFAULT_COLLAB_SESSION,
  expandedPanels: { ...DEFAULT_COLLAB_SESSION.expandedPanels },
  pinnedItemIds: [...DEFAULT_COLLAB_SESSION.pinnedItemIds],
  recentNavigation: [],
};

const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

export function subscribeCollaboration(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getCollaborationSnapshot(): CollaborationSessionState {
  return state;
}

export function setSelectedWorkspace(kind: CollaborationWorkspaceKind) {
  state = { ...state, selectedWorkspace: kind };
  emit();
}

export function toggleSidebarCollapsed() {
  state = { ...state, sidebarCollapsed: !state.sidebarCollapsed };
  emit();
}

export function setSidebarCollapsed(collapsed: boolean) {
  state = { ...state, sidebarCollapsed: collapsed };
  emit();
}

export function togglePanel(panel: CollaborationPanelId) {
  state = {
    ...state,
    expandedPanels: {
      ...state.expandedPanels,
      [panel]: !state.expandedPanels[panel],
    },
  };
  emit();
}

export function togglePinnedItem(id: string) {
  const has = state.pinnedItemIds.includes(id);
  state = {
    ...state,
    pinnedItemIds: has
      ? state.pinnedItemIds.filter((x) => x !== id)
      : [...state.pinnedItemIds, id],
  };
  emit();
}

export function setWorkspaceFilter(filter: string) {
  state = { ...state, workspaceFilter: filter };
  emit();
}

export function setMainPanelWidthPct(pct: number) {
  const clamped = Math.max(40, Math.min(85, Math.round(pct)));
  state = { ...state, mainPanelWidthPct: clamped };
  emit();
}

export function recordNavigation(href: string, label: string) {
  const entry = { href, label, at: new Date().toISOString() };
  const recentNavigation = [
    entry,
    ...state.recentNavigation.filter((n) => n.href !== href),
  ].slice(0, 8);
  state = { ...state, recentNavigation };
  emit();
}

export function navLabelForHref(href: string): string {
  const hit = COLLAB_NAV.find((n) => n.href === href);
  return hit?.label ?? href;
}

export function resolveNavId(pathname: string): CollaborationNavId {
  const exact = COLLAB_NAV.find((n) => n.href === pathname);
  if (exact) return exact.id;
  const prefix = COLLAB_NAV.find(
    (n) => n.href !== "/advisor/team" && pathname.startsWith(n.href),
  );
  return prefix?.id ?? "overview";
}

/**
 * EPIC-F008 — Administration Console UI preferences.
 * Local notes/tags only — no administration business logic.
 */

"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { AdminSectionId } from "./sections";

export type AdminNote = {
  id: string;
  text: string;
  at: string;
  resourceKey: string;
};

export type AdminTag = {
  id: string;
  label: string;
  resourceKey: string;
};

type AdminConsolePrefsState = {
  activeSection: AdminSectionId;
  leftOpen: boolean;
  rightOpen: boolean;
  selectedUserId: string | null;
  selectedRoleId: string | null;
  auditQuery: string;
  auditSubject: string;
  auditWorkflowId: string;
  auditEventType: string;
  notes: AdminNote[];
  tags: AdminTag[];
  setActiveSection: (id: AdminSectionId) => void;
  setLeftOpen: (open: boolean) => void;
  setRightOpen: (open: boolean) => void;
  toggleLeft: () => void;
  toggleRight: () => void;
  setSelectedUserId: (id: string | null) => void;
  setSelectedRoleId: (id: string | null) => void;
  setAuditFilters: (filters: {
    query?: string;
    subject?: string;
    workflowId?: string;
    eventType?: string;
  }) => void;
  addNote: (resourceKey: string, text: string) => void;
  removeNote: (id: string) => void;
  addTag: (resourceKey: string, label: string) => void;
  removeTag: (id: string) => void;
};

export const useAdminConsolePrefsStore = create<AdminConsolePrefsState>()(
  persist(
    (set) => ({
      activeSection: "overview",
      leftOpen: true,
      rightOpen: true,
      selectedUserId: null,
      selectedRoleId: null,
      auditQuery: "",
      auditSubject: "",
      auditWorkflowId: "",
      auditEventType: "",
      notes: [],
      tags: [],
      setActiveSection: (id) => set({ activeSection: id }),
      setLeftOpen: (open) => set({ leftOpen: open }),
      setRightOpen: (open) => set({ rightOpen: open }),
      toggleLeft: () => set((s) => ({ leftOpen: !s.leftOpen })),
      toggleRight: () => set((s) => ({ rightOpen: !s.rightOpen })),
      setSelectedUserId: (id) => set({ selectedUserId: id }),
      setSelectedRoleId: (id) => set({ selectedRoleId: id }),
      setAuditFilters: (filters) =>
        set((s) => ({
          auditQuery:
            filters.query !== undefined ? filters.query : s.auditQuery,
          auditSubject:
            filters.subject !== undefined ? filters.subject : s.auditSubject,
          auditWorkflowId:
            filters.workflowId !== undefined
              ? filters.workflowId
              : s.auditWorkflowId,
          auditEventType:
            filters.eventType !== undefined
              ? filters.eventType
              : s.auditEventType,
        })),
      addNote: (resourceKey, text) =>
        set((s) => {
          const trimmed = text.trim();
          const key = resourceKey.trim();
          if (!trimmed || !key) return s;
          return {
            notes: [
              {
                id: `n-${Date.now()}`,
                text: trimmed,
                at: new Date().toISOString(),
                resourceKey: key,
              },
              ...s.notes,
            ].slice(0, 40),
          };
        }),
      removeNote: (id) =>
        set((s) => ({ notes: s.notes.filter((n) => n.id !== id) })),
      addTag: (resourceKey, label) =>
        set((s) => {
          const trimmed = label.trim();
          const key = resourceKey.trim();
          if (!trimmed || !key) return s;
          if (
            s.tags.some(
              (t) =>
                t.resourceKey === key &&
                t.label.toLowerCase() === trimmed.toLowerCase(),
            )
          ) {
            return s;
          }
          return {
            tags: [
              {
                id: `t-${Date.now()}`,
                label: trimmed,
                resourceKey: key,
              },
              ...s.tags,
            ].slice(0, 40),
          };
        }),
      removeTag: (id) =>
        set((s) => ({ tags: s.tags.filter((t) => t.id !== id) })),
    }),
    {
      name: "dsp.admin-console.prefs.v1",
      partialize: (state) => ({
        leftOpen: state.leftOpen,
        rightOpen: state.rightOpen,
        activeSection: state.activeSection,
        selectedUserId: state.selectedUserId,
        selectedRoleId: state.selectedRoleId,
        auditQuery: state.auditQuery,
        auditSubject: state.auditSubject,
        auditWorkflowId: state.auditWorkflowId,
        auditEventType: state.auditEventType,
        notes: state.notes,
        tags: state.tags,
      }),
    },
  ),
);

"use client";

/**
 * EPIC-F002 — Authentication store (Zustand).
 * Mirrors AuthProvider state for subscribers; AuthProvider remains the
 * imperative API surface for existing consumers.
 */

import { create } from "zustand";

import type { AuthenticationStatus, Session, User } from "./types";

type AuthStoreState = {
  status: AuthenticationStatus;
  session: Session | null;
  user: User | null;
  setAuth: (patch: {
    status?: AuthenticationStatus;
    session?: Session | null;
    user?: User | null;
  }) => void;
  reset: () => void;
};

export const useAuthStore = create<AuthStoreState>((set) => ({
  status: "loading",
  session: null,
  user: null,
  setAuth: (patch) => set((state) => ({ ...state, ...patch })),
  reset: () =>
    set({ status: "unauthenticated", session: null, user: null }),
}));

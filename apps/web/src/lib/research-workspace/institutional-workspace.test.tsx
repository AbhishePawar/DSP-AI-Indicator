/**
 * @vitest-environment jsdom
 */
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { InstitutionalResearchWorkspace } from "@/components/institutional-research-workspace";
import {
  PUBLISH_STATUSES,
  RESEARCH_WORKSPACE_TEMPLATES,
} from "@/lib/research-workspace/templates";

vi.mock("next/navigation", () => ({
  usePathname: () => "/research/workspace",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated",
    session: { accessToken: "tok" },
    user: { id: "analyst-1", email: "a@example.com" },
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

const researchWorkspaceDashboard = vi.fn(async () => ({
  ok: true,
  result: {
    recent_notes: [],
    pending_reviews: [],
    published_reports: [],
    bookmarks: [],
    recent_copilot_conversations: [],
    recent_companies: [],
    tasks: [],
    open_comments: [],
    folders: [{ folder_id: "folder-root", name: "Research" }],
    tags: [],
  },
}));

const researchWorkspaceListNotes = vi.fn(async () => ({
  ok: true,
  result: { notes: [] },
}));

const researchWorkspaceListFolders = vi.fn(async () => ({
  ok: true,
  result: {
    folders: [{ folder_id: "folder-root", name: "Research", parent_id: null }],
  },
}));

const researchWorkspaceListBookmarks = vi.fn(async () => ({
  ok: true,
  result: { bookmarks: [] },
}));

vi.mock("@/lib/api/client", () => ({
  api: {
    researchWorkspaceDashboard: (...args: unknown[]) =>
      researchWorkspaceDashboard(...args),
    researchWorkspaceListNotes: (...args: unknown[]) =>
      researchWorkspaceListNotes(...args),
    researchWorkspaceListFolders: (...args: unknown[]) =>
      researchWorkspaceListFolders(...args),
    researchWorkspaceListBookmarks: (...args: unknown[]) =>
      researchWorkspaceListBookmarks(...args),
  },
}));

function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe("Research Workspace templates", () => {
  it("exposes institutional templates and publish statuses", () => {
    expect(RESEARCH_WORKSPACE_TEMPLATES.length).toBe(9);
    expect(PUBLISH_STATUSES).toContain("published");
  });
});

describe("InstitutionalResearchWorkspace", () => {
  beforeEach(() => {
    cleanup();
    researchWorkspaceDashboard.mockClear();
    researchWorkspaceListNotes.mockClear();
  });

  it("renders workspace shell and loads dashboard", async () => {
    renderWithClient(<InstitutionalResearchWorkspace />);
    expect(
      screen.getByTestId("institutional-research-workspace"),
    ).toBeTruthy();
    await waitFor(() => {
      expect(researchWorkspaceDashboard).toHaveBeenCalled();
      expect(researchWorkspaceListNotes).toHaveBeenCalled();
    });
    expect(screen.getByText("New note")).toBeTruthy();
    expect(screen.getByText("Folders")).toBeTruthy();
  });
});

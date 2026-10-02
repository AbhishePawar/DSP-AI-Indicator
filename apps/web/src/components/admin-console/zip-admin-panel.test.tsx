/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ApiClientError } from "@/lib/api/types";

const dashboard = vi.fn();
const listUsers = vi.fn();
const search = vi.fn();
const listSessions = vi.fn();
const adminSetStatus = vi.fn();

vi.mock("@/lib/api/adminClient", () => ({
  adminApi: {
    dashboard: (...args: unknown[]) => dashboard(...args),
    listUsers: (...args: unknown[]) => listUsers(...args),
    search: (...args: unknown[]) => search(...args),
    listSessions: (...args: unknown[]) => listSessions(...args),
  },
}));

vi.mock("@/lib/api/enterpriseAuth", () => ({
  enterpriseAuthApi: {
    adminSetStatus: (...args: unknown[]) => adminSetStatus(...args),
  },
}));

import { ZipAdminPanel } from "./ZipAdminPanel";

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ZipAdminPanel token="admin-token" />
    </QueryClientProvider>,
  );
}

describe("ZIP admin panel", () => {
  beforeEach(() => {
    cleanup();
    dashboard.mockReset();
    listUsers.mockReset();
    search.mockReset();
    listSessions.mockReset();
    adminSetStatus.mockReset();
    dashboard.mockResolvedValue({ users_count: 2 });
    listUsers.mockResolvedValue([
      {
        user_id: "u1",
        username: "ada",
        email: "ada@example.com",
        status: "active",
        created_at: "2026-08-01T00:00:00Z",
      },
    ]);
    listSessions.mockResolvedValue([
      { session_id: "s1", user_id: "u1" },
      { session_id: "s2", user_id: "u1" },
    ]);
  });

  it("renders server users and leaves unpublished metrics unavailable", async () => {
    renderPanel();
    expect(await screen.findByText("ada@example.com")).toBeTruthy();
    const total = screen.getByText("Total Users").parentElement;
    expect(total?.textContent).toContain("2");
    expect(screen.getAllByText("Data unavailable.").length).toBeGreaterThan(0);
    expect(screen.queryByText("ananya.sharma@gmail.com")).toBeNull();
    expect(screen.queryByText("1,842")).toBeNull();
    const row = screen.getByText("ada@example.com").closest("tr");
    expect(row?.textContent).toContain("2");
    expect(listUsers).toHaveBeenCalled();
    expect(search).not.toHaveBeenCalled();
  });

  it("searches through the admin API", async () => {
    search.mockResolvedValue({
      scope: "users",
      query: "ada",
      count: 1,
      results: [
        {
          user_id: "u1",
          username: "ada",
          email: "ada@example.com",
          status: "active",
        },
      ],
    });
    renderPanel();
    await screen.findByText("ada@example.com");
    fireEvent.change(screen.getByLabelText("Search users"), {
      target: { value: "ada" },
    });
    fireEvent.submit(screen.getByLabelText("Search users").closest("form")!);
    await waitFor(() => {
      expect(search).toHaveBeenCalledWith("ada", "users", { token: "admin-token" });
    });
  });

  it("saves status through the admin status API", async () => {
    adminSetStatus.mockResolvedValue({
      ok: true,
      result: { user_id: "u1", status: "disabled" },
    });
    renderPanel();
    await screen.findByText("ada@example.com");
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Status for ada@example.com"), {
      target: { value: "disabled" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(adminSetStatus).toHaveBeenCalledWith("u1", false, "admin-token");
    });
  });

  it("shows access denied when the admin API returns 403", async () => {
    const forbidden = new ApiClientError("admin permission required", 403, {
      ok: false,
      error: "FORBIDDEN",
      detail: "admin permission required",
      api_version: "v1",
      status_code: 403,
    });
    dashboard.mockRejectedValue(forbidden);
    listUsers.mockRejectedValue(forbidden);
    listSessions.mockRejectedValue(forbidden);
    renderPanel();
    expect(await screen.findByRole("heading", { name: "Access denied" })).toBeTruthy();
    expect(screen.queryByText("ada@example.com")).toBeNull();
  });
});

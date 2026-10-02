"use client";

/**
 * ZIP AdminPanel presentation over certified /api/v1/admin APIs.
 * Metrics and users come from the server. Missing fields stay "Data unavailable."
 */

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button, Input } from "@/components/ds";
import { adminApi } from "@/lib/api/adminClient";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import type { AdminSession, AdminUser } from "@/lib/api/adminTypes";
import { ApiClientError } from "@/lib/api/types";

const UNAVAILABLE = "Data unavailable.";

function shown(value: unknown): string {
  if (value === null || value === undefined) return UNAVAILABLE;
  const text = String(value).trim();
  return text ? text : UNAVAILABLE;
}

function countOrUnavailable(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value)
    ? String(value)
    : UNAVAILABLE;
}

function planOf(user: AdminUser): string {
  const meta = user.metadata;
  const plan = meta?.plan ?? meta?.subscription;
  return typeof plan === "string" && plan.trim() ? plan : UNAVAILABLE;
}

function isForbidden(err: unknown): boolean {
  return err instanceof ApiClientError && (err.status === 401 || err.status === 403);
}

function messageOf(err: unknown): string {
  if (err instanceof ApiClientError) return err.message || UNAVAILABLE;
  if (err instanceof Error && err.message) return err.message;
  return UNAVAILABLE;
}

export function ZipAdminPanel({ token }: { token?: string | null }) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [nextActive, setNextActive] = useState(true);
  const [editError, setEditError] = useState<string | null>(null);

  const dashboardQuery = useQuery({
    queryKey: ["admin", "zip-dashboard", token],
    queryFn: () => adminApi.dashboard({ token }),
  });

  const usersQuery = useQuery({
    queryKey: ["admin", "zip-users", token, query],
    queryFn: async () => {
      const q = query.trim();
      if (!q) return adminApi.listUsers({ token });
      const result = await adminApi.search(q, "users", { token });
      return (result.results ?? []) as AdminUser[];
    },
  });

  const sessionsQuery = useQuery({
    queryKey: ["admin", "zip-sessions", token],
    queryFn: () => adminApi.listSessions({ token }),
  });

  const saveStatus = useMutation({
    mutationFn: async (args: { userId: string; active: boolean }) => {
      const envelope = await enterpriseAuthApi.adminSetStatus(
        args.userId,
        args.active,
        token,
      );
      return envelope.result;
    },
    onSuccess: async () => {
      setEditError(null);
      setEditingId(null);
      await queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
    onError: (err) => {
      setEditError(messageOf(err));
    },
  });

  const forbidden =
    isForbidden(dashboardQuery.error) ||
    isForbidden(usersQuery.error) ||
    isForbidden(sessionsQuery.error);

  if (forbidden) {
    return (
      <section aria-label="Admin Panel" className="rounded-[12px] border border-[var(--border)] bg-[var(--surface)] p-5">
        <h2 className="text-lg text-[var(--fg)]">Access denied</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          This account is signed in, and the server refused administration access.
        </p>
      </section>
    );
  }

  const dash = dashboardQuery.data;
  const metrics = [
    { label: "Total Users", value: countOrUnavailable(dash?.users_count) },
    { label: "Active Today", value: UNAVAILABLE },
    { label: "Pro Subscribers", value: UNAVAILABLE },
    { label: "API Calls Today", value: UNAVAILABLE },
    { label: "Avg Latency", value: UNAVAILABLE },
  ];

  const sessions = sessionsQuery.data ?? [];
  const sessionCount = new Map<string, number>();
  for (const row of sessions as AdminSession[]) {
    if (!row.user_id) continue;
    sessionCount.set(row.user_id, (sessionCount.get(row.user_id) ?? 0) + 1);
  }

  const users = usersQuery.data ?? [];

  return (
    <section aria-label="Admin Panel" className="flex min-w-0 flex-col gap-5">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {metrics.map((metric) => (
          <div
            key={metric.label}
            className="rounded-[10px] border border-[var(--border)] bg-[var(--surface)] px-4 py-3.5"
          >
            <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.06em] text-[var(--muted)]">
              {metric.label}
            </div>
            <div className="font-mono text-xl font-semibold text-[var(--fg)]">
              {dashboardQuery.isLoading ? "…" : metric.value}
            </div>
          </div>
        ))}
      </div>

      <div className="min-w-0 overflow-hidden rounded-[12px] border border-[var(--border)] bg-[var(--surface)]">
        <form
          className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] px-5 py-3.5"
          onSubmit={(event) => {
            event.preventDefault();
            setQuery(draft.trim());
          }}
        >
          <span className="text-sm font-medium text-[var(--fg)]">User Management</span>
          <Input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Search users..."
            aria-label="Search users"
            className="w-full max-w-[220px]"
          />
        </form>

        {usersQuery.isLoading ? (
          <p className="px-5 py-4 text-sm text-[var(--muted)]" role="status">
            Loading users…
          </p>
        ) : usersQuery.isError ? (
          <p className="px-5 py-4 text-sm text-[var(--muted)]" role="alert">
            {messageOf(usersQuery.error)}
          </p>
        ) : users.length === 0 ? (
          <p className="px-5 py-4 text-sm text-[var(--muted)]">
            {query ? "No users matched that search." : UNAVAILABLE}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse text-left">
              <thead>
                <tr>
                  {["Email", "Plan", "Joined", "Sessions", "Status", ""].map((heading) => (
                    <th
                      key={heading || "actions"}
                      className="border-b border-[var(--border)] px-5 py-2 font-mono text-[10px] font-medium uppercase tracking-[0.06em] text-[var(--muted)]"
                    >
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.map((user) => {
                  const active = (user.status || "").toLowerCase() === "active";
                  const editing = editingId === user.user_id;
                  return (
                    <tr key={user.user_id} className="border-b border-[var(--border)] last:border-b-0">
                      <td className="px-5 py-3 font-mono text-sm text-[var(--fg)]">
                        {shown(user.email)}
                      </td>
                      <td className="px-5 py-3 font-mono text-xs text-[var(--muted)]">
                        {planOf(user)}
                      </td>
                      <td className="px-5 py-3 font-mono text-xs text-[var(--muted)]">
                        {shown(user.created_at)}
                      </td>
                      <td className="px-5 py-3 font-mono text-sm text-[var(--fg)]">
                        {sessionsQuery.isError
                          ? UNAVAILABLE
                          : sessionsQuery.isLoading
                            ? "…"
                            : String(sessionCount.get(user.user_id) ?? 0)}
                      </td>
                      <td className="px-5 py-3 font-mono text-xs text-[var(--fg)]">
                        {shown(user.status)}
                      </td>
                      <td className="px-5 py-3">
                        {editing ? (
                          <form
                            className="flex flex-wrap items-center gap-2"
                            onSubmit={(event) => {
                              event.preventDefault();
                              setEditError(null);
                              saveStatus.mutate({
                                userId: user.user_id,
                                active: nextActive,
                              });
                            }}
                          >
                            <label className="font-mono text-[10px] uppercase text-[var(--muted)]">
                              Status
                              <select
                                aria-label={`Status for ${user.email || user.user_id}`}
                                className="ml-2 min-h-11 rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 text-xs text-[var(--fg)]"
                                value={nextActive ? "active" : "disabled"}
                                onChange={(event) =>
                                  setNextActive(event.target.value === "active")
                                }
                              >
                                <option value="active">active</option>
                                <option value="disabled">disabled</option>
                              </select>
                            </label>
                            <Button type="submit" size="sm" disabled={saveStatus.isPending}>
                              {saveStatus.isPending ? "Saving…" : "Save"}
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                setEditingId(null);
                                setEditError(null);
                              }}
                            >
                              Cancel
                            </Button>
                          </form>
                        ) : (
                          <button
                            type="button"
                            className="min-h-11 cursor-pointer rounded-md border border-[var(--border)] bg-transparent px-2 font-[family-name:var(--font-body)] text-[11px] text-[var(--muted)]"
                            onClick={() => {
                              setEditingId(user.user_id);
                              setNextActive(active);
                              setEditError(null);
                            }}
                          >
                            Edit
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {editError ? (
          <p className="px-5 py-3 text-sm text-[var(--muted)]" role="alert">
            {editError}
          </p>
        ) : null}
      </div>
    </section>
  );
}

"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  Badge,
  Button,
  Input,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ds";
import { adminApi } from "@/lib/api/adminClient";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import type {
  AdminDashboard,
  AdminEntity,
  AdminRole,
  AdminUser,
} from "@/lib/api/adminTypes";
import {
  displayValue,
  downloadText,
  recordsToCsv,
  toJsonSnapshot,
  useAdminConsolePrefsStore,
} from "@/lib/admin-console";
import { ApiClientError } from "@/lib/api/types";
import {
  FieldRow,
  QueryError,
  SectionCard,
  WorkspaceEmpty,
  WorkspaceSkeleton,
} from "./Primitives";

function tokenOpts(token?: string | null) {
  return { token };
}

function errMessage(err: unknown): string {
  if (err instanceof ApiClientError) {
    return err.message || "Data unavailable.";
  }
  if (err instanceof Error) return err.message;
  return "Data unavailable.";
}

function entitySummary(entity: AdminEntity): string {
  const payload = entity.payload;
  if (!payload) return "Data unavailable.";
  const subject = payload.subject ?? payload.event_type ?? payload.workflow_id;
  return displayValue(subject);
}

export function OverviewSection({
  token,
}: {
  token?: string | null;
}) {
  const query = useQuery({
    queryKey: ["admin", "dashboard", token],
    queryFn: () => adminApi.dashboard(tokenOpts(token)),
  });

  if (query.isLoading) return <WorkspaceSkeleton />;
  if (query.isError) return <QueryError message={errMessage(query.error)} />;
  const data = query.data as AdminDashboard | undefined;
  if (!data) {
    return (
      <WorkspaceEmpty description="Data unavailable. No administration dashboard payload." />
    );
  }

  return (
    <div className="space-y-4">
      <SectionCard
        title="Administration Overview"
        description="Backend A010 dashboard counts only. No client aggregation."
      >
        <dl>
          <FieldRow label="Generated at" value={data.generated_at} />
          <FieldRow label="Health status" value={data.health_status} />
          <FieldRow label="Users" value={data.users_count} />
          <FieldRow label="Roles" value={data.roles_count} />
          <FieldRow label="Permissions" value={data.permissions_count} />
          <FieldRow label="Sessions" value={data.sessions_count} />
          <FieldRow label="Active sessions" value={data.active_sessions_count} />
          <FieldRow label="Audit records" value={data.audit_records_count} />
          <FieldRow
            label="Workflow records"
            value={data.workflow_records_count}
          />
          <FieldRow label="Research refs" value={data.research_refs_count} />
        </dl>
      </SectionCard>
      <SectionCard title="Dashboard metadata">
        <pre className="max-h-48 overflow-auto rounded-[var(--radius-md)] bg-[var(--surface-2)] p-3 text-xs">
          {toJsonSnapshot(data.metadata ?? { message: "Data unavailable." })}
        </pre>
      </SectionCard>
    </div>
  );
}

export function IdentitySection({
  token,
}: {
  token?: string | null;
}) {
  const selectedUserId = useAdminConsolePrefsStore((s) => s.selectedUserId);
  const setSelectedUserId = useAdminConsolePrefsStore(
    (s) => s.setSelectedUserId,
  );
  const selectedRoleId = useAdminConsolePrefsStore((s) => s.selectedRoleId);
  const setSelectedRoleId = useAdminConsolePrefsStore(
    (s) => s.setSelectedRoleId,
  );
  const [userFilter, setUserFilter] = useState("");

  const usersQuery = useQuery({
    queryKey: ["admin", "users", token],
    queryFn: () => adminApi.listUsers(tokenOpts(token)),
  });
  const rolesQuery = useQuery({
    queryKey: ["admin", "roles", token],
    queryFn: () => adminApi.listRoles(tokenOpts(token)),
  });
  const permsQuery = useQuery({
    queryKey: ["admin", "permissions", token],
    queryFn: () => adminApi.listPermissions(tokenOpts(token)),
  });
  const sessionsQuery = useQuery({
    queryKey: ["admin", "sessions", token, selectedUserId],
    queryFn: () =>
      adminApi.listSessions(tokenOpts(token), selectedUserId || undefined),
  });
  const userDetailQuery = useQuery({
    queryKey: ["admin", "user", selectedUserId, token],
    queryFn: () => adminApi.getUser(selectedUserId!, tokenOpts(token)),
    enabled: Boolean(selectedUserId),
  });
  const accessRequestsQuery = useQuery({
    queryKey: ["admin", "enterprise-access-requests", token],
    queryFn: async () => {
      const envelope = await enterpriseAuthApi.listAccessRequests(token);
      return (envelope.result || []) as Array<{
        request_id: string;
        name: string;
        email: string;
        organization?: string;
        status: string;
        created_at?: string;
        invitation_token?: string | null;
      }>;
    },
  });
  const loginHistoryQuery = useQuery({
    queryKey: ["admin", "enterprise-login-history", token, selectedUserId],
    queryFn: async () => {
      const headers: HeadersInit = {};
      if (token && token !== "__cookie__") {
        (headers as Record<string, string>).Authorization = `Bearer ${token}`;
      }
      const base =
        (await import("@/lib/env")).env.apiBaseUrl +
        `/auth/enterprise/admin/login-history${
          selectedUserId ? `?user_id=${encodeURIComponent(selectedUserId)}` : ""
        }`;
      const { cookieAuthPreferred, cookieFetchInit } = await import(
        "@/lib/auth/cookieSession"
      );
      const init = cookieAuthPreferred()
        ? cookieFetchInit({ headers })
        : { headers };
      const res = await fetch(base, init);
      const data = (await res.json()) as {
        ok?: boolean;
        result?: Array<Record<string, unknown>>;
        error?: string;
      };
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
      return data.result || [];
    },
  });

  const users = usersQuery.data ?? [];
  const roles = rolesQuery.data ?? [];
  const filteredUsers = useMemo(() => {
    const q = userFilter.trim().toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) =>
        u.username?.toLowerCase().includes(q) ||
        u.email?.toLowerCase().includes(q) ||
        u.user_id?.toLowerCase().includes(q),
    );
  }, [users, userFilter]);

  const selectedRole = roles.find((r) => r.role_id === selectedRoleId) ?? null;

  if (usersQuery.isLoading || rolesQuery.isLoading) {
    return <WorkspaceSkeleton />;
  }

  return (
    <div className="space-y-4">
      <SectionCard
        title="User List"
        description="GET /admin/users — display only."
        action={
          <Input
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            placeholder="Filter users"
            aria-label="Filter users"
            className="w-40"
          />
        }
      >
        {usersQuery.isError ? (
          <QueryError message={errMessage(usersQuery.error)} />
        ) : filteredUsers.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. No users returned." />
        ) : (
          <Table aria-label="Administration users">
            <TableHeader>
              <TableRow>
                <TableHead>Username</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Roles</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredUsers.map((u: AdminUser) => (
                <TableRow key={u.user_id}>
                  <TableCell className="font-medium">
                    {u.username || "Data unavailable."}
                  </TableCell>
                  <TableCell>{u.email || "Data unavailable."}</TableCell>
                  <TableCell>{u.status || "Data unavailable."}</TableCell>
                  <TableCell className="text-xs">
                    {(u.roles || []).join(", ") || "Data unavailable."}
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setSelectedUserId(u.user_id)}
                    >
                      Details
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </SectionCard>

      <SectionCard title="User Details">
        {!selectedUserId ? (
          <WorkspaceEmpty description="Select a user to inspect details." />
        ) : userDetailQuery.isLoading ? (
          <WorkspaceSkeleton />
        ) : userDetailQuery.isError ? (
          <QueryError message={errMessage(userDetailQuery.error)} />
        ) : userDetailQuery.data ? (
          <dl>
            <FieldRow label="User ID" value={userDetailQuery.data.user_id} />
            <FieldRow label="Username" value={userDetailQuery.data.username} />
            <FieldRow label="Email" value={userDetailQuery.data.email} />
            <FieldRow
              label="Display name"
              value={userDetailQuery.data.display_name}
            />
            <FieldRow label="Status" value={userDetailQuery.data.status} />
            <FieldRow
              label="Created"
              value={userDetailQuery.data.created_at}
            />
            <FieldRow
              label="Updated"
              value={userDetailQuery.data.updated_at}
            />
            <FieldRow
              label="Last login"
              value={userDetailQuery.data.last_login}
            />
            <FieldRow
              label="Roles"
              value={(userDetailQuery.data.roles || []).join(", ")}
            />
          </dl>
        ) : (
          <WorkspaceEmpty />
        )}
      </SectionCard>

      <SectionCard title="Role List" description="GET /admin/roles">
        {rolesQuery.isError ? (
          <QueryError message={errMessage(rolesQuery.error)} />
        ) : roles.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. No roles returned." />
        ) : (
          <Table aria-label="Administration roles">
            <TableHeader>
              <TableRow>
                <TableHead>Role</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Configurable</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {roles.map((r: AdminRole) => (
                <TableRow key={r.role_id}>
                  <TableCell className="font-mono text-xs">
                    {r.role_id}
                  </TableCell>
                  <TableCell>{r.name || "Data unavailable."}</TableCell>
                  <TableCell>
                    {r.configurable === undefined
                      ? "Data unavailable."
                      : String(r.configurable)}
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setSelectedRoleId(r.role_id)}
                    >
                      Details
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </SectionCard>

      <SectionCard title="Role Details">
        {!selectedRole ? (
          <WorkspaceEmpty description="Select a role to inspect permissions." />
        ) : (
          <div className="space-y-2">
            <dl>
              <FieldRow label="Role ID" value={selectedRole.role_id} />
              <FieldRow label="Name" value={selectedRole.name} />
            </dl>
            <div className="flex flex-wrap gap-1">
              {(selectedRole.permissions || []).length === 0 ? (
                <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
              ) : (
                selectedRole.permissions!.map((p) => (
                  <Badge key={p} variant="outline">
                    {p}
                  </Badge>
                ))
              )}
            </div>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Permission Viewer" description="GET /admin/permissions">
        {permsQuery.isLoading ? (
          <WorkspaceSkeleton />
        ) : permsQuery.isError ? (
          <QueryError message={errMessage(permsQuery.error)} />
        ) : (permsQuery.data || []).length === 0 ? (
          <WorkspaceEmpty />
        ) : (
          <div className="flex flex-wrap gap-1" aria-label="Platform permissions">
            {permsQuery.data!.map((p) => (
              <Badge key={p} variant="outline">
                {p}
              </Badge>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard
        title="Session Viewer"
        description="GET /admin/sessions — optionally scoped to selected user."
      >
        {sessionsQuery.isLoading ? (
          <WorkspaceSkeleton />
        ) : sessionsQuery.isError ? (
          <QueryError message={errMessage(sessionsQuery.error)} />
        ) : (sessionsQuery.data || []).length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. No sessions returned." />
        ) : (
          <Table aria-label="Administration sessions">
            <TableHeader>
              <TableRow>
                <TableHead>Session</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Expires</TableHead>
                <TableHead>Revoked</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sessionsQuery.data!.map((s) => (
                <TableRow key={s.session_id}>
                  <TableCell className="font-mono text-xs">
                    {s.session_id}
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {s.user_id}
                  </TableCell>
                  <TableCell>{s.created_at || "Data unavailable."}</TableCell>
                  <TableCell>{s.expires_at || "Data unavailable."}</TableCell>
                  <TableCell>
                    {s.revoked === undefined
                      ? "Data unavailable."
                      : String(s.revoked)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </SectionCard>

      <SectionCard
        title="Enterprise access requests"
        description="POST /auth/enterprise/access-requests — approve or reject pending enterprise onboarding."
      >
        {accessRequestsQuery.isLoading ? (
          <WorkspaceSkeleton />
        ) : accessRequestsQuery.isError ? (
          <QueryError message={errMessage(accessRequestsQuery.error)} />
        ) : (accessRequestsQuery.data || []).length === 0 ? (
          <WorkspaceEmpty description="No access requests." />
        ) : (
          <Table aria-label="Enterprise access requests">
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {(accessRequestsQuery.data || []).map((req) => (
                <TableRow key={req.request_id}>
                  <TableCell>{req.name}</TableCell>
                  <TableCell>{req.email}</TableCell>
                  <TableCell>{req.status}</TableCell>
                  <TableCell>{req.created_at || "Data unavailable."}</TableCell>
                  <TableCell className="space-x-1">
                    {req.status === "pending" ? (
                      <>
                        <Button
                          size="sm"
                          onClick={async () => {
                            await enterpriseAuthApi.decideAccessRequest(
                              req.request_id,
                              { approve: true, role: "enterprise_client" },
                              token,
                            );
                            await accessRequestsQuery.refetch();
                          }}
                        >
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={async () => {
                            await enterpriseAuthApi.decideAccessRequest(
                              req.request_id,
                              { approve: false },
                              token,
                            );
                            await accessRequestsQuery.refetch();
                          }}
                        >
                          Reject
                        </Button>
                      </>
                    ) : req.invitation_token ? (
                      <span className="font-mono text-xs">
                        invite:{req.invitation_token.slice(0, 8)}…
                      </span>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </SectionCard>

      <SectionCard
        title="Login history"
        description="GET /auth/enterprise/admin/login-history — device/provider audit trail."
      >
        {loginHistoryQuery.isLoading ? (
          <WorkspaceSkeleton />
        ) : loginHistoryQuery.isError ? (
          <QueryError message={errMessage(loginHistoryQuery.error)} />
        ) : (loginHistoryQuery.data || []).length === 0 ? (
          <WorkspaceEmpty description="No login history records." />
        ) : (
          <Table aria-label="Login history">
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Success</TableHead>
                <TableHead>When</TableHead>
                <TableHead>Device</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(loginHistoryQuery.data || []).slice(0, 50).map((row) => (
                <TableRow key={String(row.entry_id)}>
                  <TableCell className="font-mono text-xs">
                    {String(row.user_id || "")}
                  </TableCell>
                  <TableCell>{String(row.provider || "")}</TableCell>
                  <TableCell>{String(row.success)}</TableCell>
                  <TableCell>{String(row.created_at || "")}</TableCell>
                  <TableCell>{String(row.device_label || "—")}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </SectionCard>
    </div>
  );
}

export function AuditSection({ token }: { token?: string | null }) {
  const auditQuery = useAdminConsolePrefsStore((s) => s.auditQuery);
  const auditSubject = useAdminConsolePrefsStore((s) => s.auditSubject);
  const auditWorkflowId = useAdminConsolePrefsStore((s) => s.auditWorkflowId);
  const auditEventType = useAdminConsolePrefsStore((s) => s.auditEventType);
  const setAuditFilters = useAdminConsolePrefsStore((s) => s.setAuditFilters);
  const [draftQuery, setDraftQuery] = useState(auditQuery);
  const [draftSubject, setDraftSubject] = useState(auditSubject);
  const [draftWorkflow, setDraftWorkflow] = useState(auditWorkflowId);
  const [draftEvent, setDraftEvent] = useState(auditEventType);

  const filters = {
    query: auditQuery || undefined,
    subject: auditSubject || undefined,
    workflow_id: auditWorkflowId || undefined,
    event_type: auditEventType || undefined,
  };

  const listQuery = useQuery({
    queryKey: ["admin", "audit", filters, token],
    queryFn: () => adminApi.listAudit(filters, tokenOpts(token)),
  });
  const timelineQuery = useQuery({
    queryKey: ["admin", "timeline", token],
    queryFn: () => adminApi.timeline(100, tokenOpts(token)),
  });

  const applyFilters = () => {
    setAuditFilters({
      query: draftQuery,
      subject: draftSubject,
      workflowId: draftWorkflow,
      eventType: draftEvent,
    });
  };

  return (
    <div className="space-y-4">
      <SectionCard
        title="Search & Filter Audit Events"
        description="Filters are sent to GET /admin/audit — no client invention."
      >
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            value={draftQuery}
            onChange={(e) => setDraftQuery(e.target.value)}
            placeholder="Query"
            aria-label="Search audit events"
          />
          <Input
            value={draftSubject}
            onChange={(e) => setDraftSubject(e.target.value)}
            placeholder="Subject"
            aria-label="Filter audit by subject"
          />
          <Input
            value={draftWorkflow}
            onChange={(e) => setDraftWorkflow(e.target.value)}
            placeholder="Workflow ID"
            aria-label="Filter audit by workflow"
          />
          <Input
            value={draftEvent}
            onChange={(e) => setDraftEvent(e.target.value)}
            placeholder="Event type"
            aria-label="Filter audit by event type"
          />
        </div>
        <div className="mt-2">
          <Button size="sm" onClick={applyFilters}>
            Apply filters
          </Button>
        </div>
      </SectionCard>

      <SectionCard title="Audit Log Viewer">
        {listQuery.isLoading ? (
          <WorkspaceSkeleton />
        ) : listQuery.isError ? (
          <QueryError message={errMessage(listQuery.error)} />
        ) : (listQuery.data || []).length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. No audit records for current filters." />
        ) : (
          <Table aria-label="Audit log">
            <TableHeader>
              <TableRow>
                <TableHead>Entity</TableHead>
                <TableHead>Kind</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Summary</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {listQuery.data!.map((row, idx) => (
                <TableRow key={row.entity_id || `audit-${idx}`}>
                  <TableCell className="font-mono text-xs">
                    {row.entity_id || "Data unavailable."}
                  </TableCell>
                  <TableCell>{row.kind || "Data unavailable."}</TableCell>
                  <TableCell>{row.created_at || "Data unavailable."}</TableCell>
                  <TableCell className="text-xs">
                    {entitySummary(row)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </SectionCard>

      <SectionCard title="Activity Timeline" description="GET /admin/timeline">
        {timelineQuery.isLoading ? (
          <WorkspaceSkeleton />
        ) : timelineQuery.isError ? (
          <QueryError message={errMessage(timelineQuery.error)} />
        ) : (timelineQuery.data || []).length === 0 ? (
          <WorkspaceEmpty />
        ) : (
          <ol className="space-y-2" aria-label="Activity timeline">
            {timelineQuery.data!.map((item, idx) => (
              <li
                key={`${item.entity_id || "t"}-${idx}`}
                className="rounded-[var(--radius-md)] border border-[var(--border)] p-3 text-sm"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Badge variant="outline">
                    {item.kind || "Data unavailable."}
                  </Badge>
                  <span className="text-xs text-[var(--muted)]">
                    {item.created_at || "Data unavailable."}
                  </span>
                </div>
                <p className="mt-1 font-mono text-xs">
                  {item.entity_id || "Data unavailable."}
                </p>
                <pre className="mt-2 max-h-24 overflow-auto text-xs text-[var(--muted)]">
                  {toJsonSnapshot(item.summary ?? { message: "Data unavailable." })}
                </pre>
              </li>
            ))}
          </ol>
        )}
      </SectionCard>

      <SectionCard title="Audit Metadata">
        {listQuery.data?.[0] ? (
          <pre className="max-h-64 overflow-auto rounded-[var(--radius-md)] bg-[var(--surface-2)] p-3 text-xs">
            {toJsonSnapshot({
              entity_id: listQuery.data[0].entity_id,
              kind: listQuery.data[0].kind,
              version: listQuery.data[0].version,
              refs: listQuery.data[0].refs,
              provenance: listQuery.data[0].provenance,
            })}
          </pre>
        ) : (
          <WorkspaceEmpty description="Data unavailable. Select filters that return audit rows." />
        )}
      </SectionCard>
    </div>
  );
}

export function PlatformSection({ token }: { token?: string | null }) {
  const healthQuery = useQuery({
    queryKey: ["admin", "health", token],
    queryFn: () => adminApi.health(tokenOpts(token)),
  });
  const versionsQuery = useQuery({
    queryKey: ["admin", "versions", token],
    queryFn: () => adminApi.versions(tokenOpts(token)),
  });
  const configQuery = useQuery({
    queryKey: ["admin", "configuration", token],
    queryFn: () => adminApi.configuration(tokenOpts(token)),
  });
  const flagsQuery = useQuery({
    queryKey: ["admin", "feature-flags", token],
    queryFn: () => adminApi.featureFlags(tokenOpts(token)),
  });

  return (
    <div className="space-y-4">
      <SectionCard title="Platform Health" description="GET /admin/health">
        {healthQuery.isLoading ? (
          <WorkspaceSkeleton />
        ) : healthQuery.isError ? (
          <QueryError message={errMessage(healthQuery.error)} />
        ) : !healthQuery.data ? (
          <WorkspaceEmpty />
        ) : (
          <div className="space-y-3">
            <dl>
              <FieldRow label="Status" value={healthQuery.data.status} />
              <FieldRow
                label="Ready"
                value={
                  healthQuery.data.ready === undefined
                    ? undefined
                    : String(healthQuery.data.ready)
                }
              />
            </dl>
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
                Service status
              </p>
              {(healthQuery.data.checks || []).length === 0 ? (
                <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
              ) : (
                <ul className="space-y-2" aria-label="Service status checks">
                  {healthQuery.data.checks!.map((c, idx) => (
                    <li
                      key={`${c.name || "check"}-${idx}`}
                      className="flex justify-between gap-3 border-b border-[var(--border)] py-2 text-sm"
                    >
                      <span>{c.name || "Data unavailable."}</span>
                      <span>
                        {c.status || "Data unavailable."}
                        {c.message ? ` — ${c.message}` : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Version Information" description="GET /admin/versions">
        {versionsQuery.isLoading ? (
          <WorkspaceSkeleton />
        ) : versionsQuery.isError ? (
          <QueryError message={errMessage(versionsQuery.error)} />
        ) : (versionsQuery.data?.packages || []).length === 0 ? (
          <WorkspaceEmpty />
        ) : (
          <Table aria-label="Package versions">
            <TableHeader>
              <TableRow>
                <TableHead>Package</TableHead>
                <TableHead>Version</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {versionsQuery.data!.packages!.map((p, idx) => (
                <TableRow key={`${p.package || "pkg"}-${idx}`}>
                  <TableCell>{p.package || "Data unavailable."}</TableCell>
                  <TableCell className="font-mono text-xs">
                    {p.version || "Data unavailable."}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </SectionCard>

      <SectionCard
        title="Configuration Viewer"
        description="GET /admin/configuration — secrets remain Data unavailable."
      >
        {configQuery.isLoading ? (
          <WorkspaceSkeleton />
        ) : configQuery.isError ? (
          <QueryError message={errMessage(configQuery.error)} />
        ) : configQuery.data?.message &&
          (!configQuery.data.items || configQuery.data.items.length === 0) ? (
          <WorkspaceEmpty description={configQuery.data.message} />
        ) : (configQuery.data?.items || []).length === 0 ? (
          <WorkspaceEmpty />
        ) : (
          <Table aria-label="Configuration items">
            <TableHeader>
              <TableRow>
                <TableHead>Key</TableHead>
                <TableHead>Set</TableHead>
                <TableHead>Value</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {configQuery.data!.items!.map((item, idx) => (
                <TableRow key={`${item.key || "cfg"}-${idx}`}>
                  <TableCell className="font-mono text-xs">
                    {item.key || "Data unavailable."}
                  </TableCell>
                  <TableCell>
                    {item.set === undefined
                      ? "Data unavailable."
                      : String(item.set)}
                  </TableCell>
                  <TableCell className="text-xs">
                    {item.value || "Data unavailable."}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </SectionCard>

      <SectionCard title="Feature Flags" description="GET /admin/feature-flags">
        {flagsQuery.isLoading ? (
          <WorkspaceSkeleton />
        ) : flagsQuery.isError ? (
          <QueryError message={errMessage(flagsQuery.error)} />
        ) : flagsQuery.data?.message &&
          Object.keys(flagsQuery.data.flags || {}).length === 0 ? (
          <WorkspaceEmpty description={flagsQuery.data.message} />
        ) : Object.keys(flagsQuery.data?.flags || {}).length === 0 ? (
          <WorkspaceEmpty />
        ) : (
          <dl>
            <FieldRow label="Source" value={flagsQuery.data?.source} />
            {Object.entries(flagsQuery.data!.flags!).map(([key, value]) => (
              <FieldRow key={key} label={key} value={String(value)} />
            ))}
          </dl>
        )}
      </SectionCard>

      <SectionCard title="Environment Information">
        <dl>
          <FieldRow
            label="Config source"
            value={configQuery.data?.source}
          />
          <FieldRow
            label="Flag source"
            value={flagsQuery.data?.source}
          />
          <FieldRow
            label="API contract"
            value="v1.0.0"
          />
        </dl>
      </SectionCard>
    </div>
  );
}

export function MetricsSection({ token }: { token?: string | null }) {
  const query = useQuery({
    queryKey: ["admin", "metrics", token],
    queryFn: () => adminApi.metrics(tokenOpts(token)),
  });
  const healthQuery = useQuery({
    queryKey: ["admin", "health", token],
    queryFn: () => adminApi.health(tokenOpts(token)),
  });

  if (query.isLoading) return <WorkspaceSkeleton />;
  if (query.isError) return <QueryError message={errMessage(query.error)} />;
  if (!query.data) return <WorkspaceEmpty />;

  const m = query.data;
  return (
    <div className="space-y-4">
      <SectionCard
        title="System Metrics"
        description="GET /admin/metrics — backend counts only."
      >
        <dl>
          <FieldRow label="Users" value={m.users} />
          <FieldRow label="Sessions total" value={m.sessions_total} />
          <FieldRow label="Sessions active" value={m.sessions_active} />
          <FieldRow label="Audit records" value={m.audit_records} />
          <FieldRow label="Workflow records" value={m.workflow_records} />
          <FieldRow label="Approval history" value={m.approval_history} />
          <FieldRow label="Research refs" value={m.research_refs} />
          <FieldRow label="Citations" value={m.citations} />
          <FieldRow label="Provenance" value={m.provenance} />
          <FieldRow label="Metadata entities" value={m.metadata_entities} />
        </dl>
      </SectionCard>
      <SectionCard title="Health Summary">
        {healthQuery.isLoading ? (
          <WorkspaceSkeleton />
        ) : healthQuery.isError ? (
          <QueryError message={errMessage(healthQuery.error)} />
        ) : (
          <dl>
            <FieldRow label="Status" value={healthQuery.data?.status} />
            <FieldRow
              label="Ready"
              value={
                healthQuery.data?.ready === undefined
                  ? undefined
                  : String(healthQuery.data.ready)
              }
            />
          </dl>
        )}
      </SectionCard>
      <SectionCard title="Runtime / Storage / Background">
        <WorkspaceEmpty description="Data unavailable. No dedicated runtime, storage, or background-service fields beyond A010 metrics and health checks." />
      </SectionCard>
    </div>
  );
}

function workflowFields(entity: AdminEntity) {
  const p = entity.payload || {};
  return {
    workflowId: displayValue(p.workflow_id),
    templateId: displayValue(p.template_id),
    subject: displayValue(p.subject),
    stage: displayValue(p.stage),
  };
}

export function WorkflowSection({ token }: { token?: string | null }) {
  const query = useQuery({
    queryKey: ["admin", "workflow-history", token],
    queryFn: () => adminApi.workflowHistory(tokenOpts(token)),
  });

  if (query.isLoading) return <WorkspaceSkeleton />;
  if (query.isError) return <QueryError message={errMessage(query.error)} />;
  const rows = query.data || [];

  const pending = rows.filter((r) => {
    const stage = String(r.payload?.stage || "").toLowerCase();
    return stage.includes("pending") || stage.includes("review");
  });
  const approvals = rows.filter((r) => {
    const stage = String(r.payload?.stage || "").toLowerCase();
    return stage.includes("approv");
  });

  return (
    <div className="space-y-4">
      <SectionCard
        title="Workflow History"
        description="GET /admin/workflow-history — metadata only."
      >
        {rows.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. No workflow records returned." />
        ) : (
          <Table aria-label="Workflow history">
            <TableHeader>
              <TableRow>
                <TableHead>Workflow</TableHead>
                <TableHead>Subject</TableHead>
                <TableHead>Stage</TableHead>
                <TableHead>Updated</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r, idx) => {
                const f = workflowFields(r);
                return (
                  <TableRow key={r.entity_id || `wf-${idx}`}>
                    <TableCell className="font-mono text-xs">
                      {f.workflowId}
                    </TableCell>
                    <TableCell>{f.subject}</TableCell>
                    <TableCell>{f.stage}</TableCell>
                    <TableCell>
                      {r.updated_at || r.created_at || "Data unavailable."}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </SectionCard>
      <SectionCard title="Pending Items">
        {pending.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. No pending-stage workflow rows in backend payload." />
        ) : (
          <ul className="space-y-1 text-sm">
            {pending.map((r, idx) => (
              <li key={r.entity_id || `pending-${idx}`}>
                {workflowFields(r).workflowId} · {workflowFields(r).stage}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Recent Approvals">
        {approvals.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. No approval-stage workflow rows in backend payload. No dedicated approval-history HTTP route." />
        ) : (
          <ul className="space-y-1 text-sm">
            {approvals.map((r, idx) => (
              <li key={r.entity_id || `appr-${idx}`}>
                {workflowFields(r).workflowId} · {workflowFields(r).stage}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Workflow Activity">
        <p className="text-sm text-[var(--muted)]">
          Activity is the workflow history list above. Counts are not computed
          client-side beyond listing backend rows.
        </p>
      </SectionCard>
    </div>
  );
}

export function ResearchRefsSection({ token }: { token?: string | null }) {
  const query = useQuery({
    queryKey: ["admin", "research-archive", token],
    queryFn: () => adminApi.researchArchive(tokenOpts(token)),
  });
  const healthQuery = useQuery({
    queryKey: ["admin", "health", token],
    queryFn: () => adminApi.health(tokenOpts(token)),
  });

  if (query.isLoading) return <WorkspaceSkeleton />;
  if (query.isError) return <QueryError message={errMessage(query.error)} />;
  const rows = query.data || [];

  return (
    <div className="space-y-4">
      <SectionCard
        title="Research / Archive References"
        description="GET /admin/research-archive — metadata refs only, never research bodies."
      >
        {rows.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. No research archive references returned." />
        ) : (
          <Table aria-label="Research archive references">
            <TableHeader>
              <TableRow>
                <TableHead>Entity</TableHead>
                <TableHead>Kind</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Refs</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r, idx) => (
                <TableRow key={r.entity_id || `ref-${idx}`}>
                  <TableCell className="font-mono text-xs">
                    {r.entity_id || "Data unavailable."}
                  </TableCell>
                  <TableCell>{r.kind || "Data unavailable."}</TableCell>
                  <TableCell>{r.created_at || "Data unavailable."}</TableCell>
                  <TableCell className="max-w-xs truncate text-xs">
                    {displayValue(r.refs)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </SectionCard>
      <SectionCard title="Monitoring Status">
        {healthQuery.isLoading ? (
          <WorkspaceSkeleton />
        ) : healthQuery.isError ? (
          <QueryError message={errMessage(healthQuery.error)} />
        ) : (
          <dl>
            <FieldRow label="Health" value={healthQuery.data?.status} />
            <FieldRow
              label="Ready"
              value={
                healthQuery.data?.ready === undefined
                  ? undefined
                  : String(healthQuery.data.ready)
              }
            />
          </dl>
        )}
      </SectionCard>
      <SectionCard title="Recent Reports">
        <WorkspaceEmpty description="Data unavailable. No admin recent-reports endpoint; research bodies are intentionally excluded from A010." />
      </SectionCard>
    </div>
  );
}

export function ExportSection({ token }: { token?: string | null }) {
  const auditQuery = useAdminConsolePrefsStore((s) => s.auditQuery);
  const auditSubject = useAdminConsolePrefsStore((s) => s.auditSubject);
  const auditWorkflowId = useAdminConsolePrefsStore((s) => s.auditWorkflowId);
  const auditEventType = useAdminConsolePrefsStore((s) => s.auditEventType);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filters = {
    query: auditQuery || undefined,
    subject: auditSubject || undefined,
    workflow_id: auditWorkflowId || undefined,
    event_type: auditEventType || undefined,
  };

  const exportAudit = async (format: "json" | "csv") => {
    setBusy(true);
    setError(null);
    try {
      const payload = await adminApi.exportAudit(filters, tokenOpts(token));
      if (format === "json") {
        downloadText(
          "admin-audit-export.json",
          toJsonSnapshot(payload),
          "application/json;charset=utf-8",
        );
      } else {
        const records = Array.isArray(payload.records) ? payload.records : [];
        downloadText(
          "admin-audit-export.csv",
          recordsToCsv(records),
          "text/csv;charset=utf-8",
        );
      }
    } catch (err) {
      setError(errMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const exportLogsJson = async () => {
    setBusy(true);
    setError(null);
    try {
      const records = await adminApi.listAudit(filters, tokenOpts(token));
      downloadText(
        "admin-audit-logs.json",
        toJsonSnapshot(records),
        "application/json;charset=utf-8",
      );
    } catch (err) {
      setError(errMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <SectionCard
        title="Export"
        description="Exports backend A010 payloads only. Uses current audit filters."
      >
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            disabled={busy}
            onClick={() => void exportAudit("json")}
          >
            Export audit metadata (JSON)
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => void exportAudit("csv")}
          >
            Export audit metadata (CSV)
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => void exportLogsJson()}
          >
            Export logs (JSON)
          </Button>
        </div>
        {error ? (
          <p className="mt-3 text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
        ) : null}
        <p className="mt-3 text-xs text-[var(--muted)]">
          Excel is not a separate A010 format — use CSV. No client-side scoring
          or fabricated rows.
        </p>
      </SectionCard>
    </div>
  );
}

/** P5.1 — Closed Beta admin dashboard (invites, feedback, analytics). */
export function BetaSection({ token }: { token?: string | null }) {
  const [inviteIdentity, setInviteIdentity] = useState("");
  const [inviteMsg, setInviteMsg] = useState<string | null>(null);

  const dashQuery = useQuery({
    queryKey: ["admin", "beta", "dashboard", token],
    queryFn: async () => {
      const { betaApi } = await import("@/lib/beta/betaApi");
      return betaApi.dashboard(token);
    },
    retry: false,
  });
  const invitesQuery = useQuery({
    queryKey: ["admin", "beta", "invites", token],
    queryFn: async () => {
      const { betaApi } = await import("@/lib/beta/betaApi");
      return betaApi.invites(token);
    },
    retry: false,
  });
  const analyticsQuery = useQuery({
    queryKey: ["admin", "beta", "analytics", token],
    queryFn: async () => {
      const { betaApi } = await import("@/lib/beta/betaApi");
      return betaApi.analytics(token);
    },
    retry: false,
  });
  const issuesQuery = useQuery({
    queryKey: ["admin", "beta", "issues", token],
    queryFn: async () => {
      const { betaApi } = await import("@/lib/beta/betaApi");
      return betaApi.issues(token);
    },
    retry: false,
  });
  const rcQuery = useQuery({
    queryKey: ["admin", "beta", "rc", token],
    queryFn: async () => {
      const { betaApi } = await import("@/lib/beta/betaApi");
      return betaApi.rcAssessment(token);
    },
    retry: false,
  });

  async function createInvite() {
    setInviteMsg(null);
    try {
      const { betaApi } = await import("@/lib/beta/betaApi");
      await betaApi.createInvite(
        {
          email_or_username: inviteIdentity,
          status: "approved",
          role: "beta_participant",
        },
        token,
      );
      setInviteIdentity("");
      setInviteMsg("Invite approved.");
      await invitesQuery.refetch();
      await dashQuery.refetch();
    } catch (err) {
      setInviteMsg(err instanceof Error ? err.message : "Invite failed");
    }
  }

  async function setIssueStatus(id: string, status: string) {
    const { betaApi } = await import("@/lib/beta/betaApi");
    await betaApi.patchIssue(id, { status }, token);
    await issuesQuery.refetch();
    await dashQuery.refetch();
  }

  const d = dashQuery.data;

  return (
    <div className="space-y-4">
      <SectionCard
        title="Closed Beta dashboard"
        description="P5.1 ops metrics — no investment decision content"
      >
        {dashQuery.isLoading ? <WorkspaceSkeleton /> : null}
        {dashQuery.isError ? (
          <QueryError message={errMessage(dashQuery.error)} />
        ) : d ? (
          <dl>
            <FieldRow label="Active beta users" value={String(d.active_beta_users)} />
            <FieldRow label="Pending invites" value={String(d.pending_invites)} />
            <FieldRow label="Daily active users" value={String(d.daily_active_users)} />
            <FieldRow label="Reports generated" value={String(d.reports_generated)} />
            <FieldRow label="Failed analyses" value={String(d.failed_analyses)} />
            <FieldRow label="Export usage" value={String(d.export_usage)} />
            <FieldRow label="Feedback received" value={String(d.feedback_received)} />
            <FieldRow
              label="Avg feedback rating"
              value={
                d.average_feedback_rating == null
                  ? "Unavailable"
                  : String(d.average_feedback_rating)
              }
            />
            <FieldRow
              label="Open critical issues"
              value={String(d.open_critical_issues)}
            />
          </dl>
        ) : (
          <WorkspaceEmpty />
        )}
      </SectionCard>

      <SectionCard title="Invitations" description="Approve / activate participants">
        <div className="flex flex-wrap gap-2">
          <Input
            value={inviteIdentity}
            onChange={(e) => setInviteIdentity(e.target.value)}
            placeholder="email or username"
            aria-label="Invite identity"
            className="min-w-[12rem] flex-1"
          />
          <Button size="sm" onClick={() => void createInvite()} disabled={!inviteIdentity.trim()}>
            Approve invite
          </Button>
        </div>
        {inviteMsg ? (
          <p className="mt-2 text-sm" role="status">
            {inviteMsg}
          </p>
        ) : null}
        {invitesQuery.isLoading ? <WorkspaceSkeleton /> : null}
        {invitesQuery.data && invitesQuery.data.length === 0 ? (
          <WorkspaceEmpty description="No invites yet." />
        ) : null}
        {invitesQuery.data && invitesQuery.data.length > 0 ? (
          <Table className="mt-3">
            <TableHeader>
              <TableRow>
                <TableHead>Identity</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invitesQuery.data.slice(0, 20).map((row) => (
                <TableRow key={String(row.id)}>
                  <TableCell>{String(row.email_or_username)}</TableCell>
                  <TableCell>{String(row.role)}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{String(row.status)}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : null}
      </SectionCard>

      <SectionCard title="Issue workflow" description="New → Triaged → In Progress → Resolved → Closed">
        {issuesQuery.data && issuesQuery.data.length === 0 ? (
          <WorkspaceEmpty description="No issues." />
        ) : null}
        {issuesQuery.data && issuesQuery.data.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Advance</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {issuesQuery.data.slice(0, 15).map((row) => (
                <TableRow key={String(row.id)}>
                  <TableCell>{String(row.title)}</TableCell>
                  <TableCell>{String(row.severity)}</TableCell>
                  <TableCell>{String(row.status)}</TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        void setIssueStatus(
                          String(row.id),
                          nextIssueStatus(String(row.status)),
                        )
                      }
                    >
                      Next
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : null}
      </SectionCard>

      <SectionCard title="Beta analytics" description="Aggregate ops only">
        {analyticsQuery.isLoading ? <WorkspaceSkeleton /> : null}
        {analyticsQuery.data ? (
          <dl>
            {Object.entries(analyticsQuery.data).map(([key, value]) => (
              <FieldRow
                key={key}
                label={key}
                value={
                  typeof value === "object"
                    ? JSON.stringify(value)
                    : value == null
                      ? "Unavailable"
                      : String(value)
                }
              />
            ))}
          </dl>
        ) : null}
      </SectionCard>

      <SectionCard
        title="Release Candidate assessment"
        description="P5.2 readiness from beta metrics"
      >
        {rcQuery.isLoading ? <WorkspaceSkeleton /> : null}
        {rcQuery.data ? (
          <dl>
            <FieldRow
              label="Decision"
              value={String(rcQuery.data.decision ?? "Unavailable")}
            />
            <FieldRow
              label="Overall score"
              value={String(rcQuery.data.overall_score ?? "Unavailable")}
            />
            <FieldRow
              label="Rationale"
              value={String(rcQuery.data.rationale ?? "Unavailable")}
            />
          </dl>
        ) : null}
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => void exportBetaSnapshot(token)}
          >
            Export beta snapshot
          </Button>
        </div>
      </SectionCard>
    </div>
  );
}

async function exportBetaSnapshot(token?: string | null) {
  const { betaApi } = await import("@/lib/beta/betaApi");
  const snap = await betaApi.snapshot(token);
  downloadText(
    `dsp-beta-snapshot-${new Date().toISOString().slice(0, 10)}.json`,
    JSON.stringify(snap, null, 2),
    "application/json",
  );
}

function nextIssueStatus(current: string): string {
  const order = ["new", "triaged", "in_progress", "resolved", "closed"];
  const idx = order.indexOf(current);
  if (idx < 0) return "triaged";
  return order[Math.min(idx + 1, order.length - 1)]!;
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  Alert,
  Avatar,
  AvatarFallback,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  FormField,
  Input,
  PageLayout,
  PasswordInput,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  ValidationMessage,
} from "@/components/ds";
import { AuthGuard } from "@/components/auth/ProtectedRoute";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import { rbacAuthApi } from "@/lib/api/rbacAuth";
import type { RbacSession } from "@/lib/api/rbacTypes";
import { useAuth } from "@/lib/auth/AuthProvider";
import { tokenStatus } from "@/lib/auth/sessionStore";
import { sessionStatusLabel } from "@/lib/auth/types";
import { env } from "@/lib/env";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:items-baseline sm:justify-between sm:gap-4">
      <dt className="text-sm text-[var(--muted)]">{label}</dt>
      <dd className="font-mono text-sm break-all text-[var(--fg)]">{value}</dd>
    </div>
  );
}

function ProfileContent() {
  const router = useRouter();
  const { user, session, status, logout, refreshSession, loadProfile } =
    useAuth();
  const [sessions, setSessions] = useState<RbacSession[] | null>(null);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [devices, setDevices] = useState<Record<string, unknown>[]>([]);
  const [history, setHistory] = useState<Record<string, unknown>[]>([]);
  const [linked, setLinked] = useState<Record<string, unknown>[]>([]);
  const [accountMsg, setAccountMsg] = useState<string | null>(null);
  const [accountErr, setAccountErr] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const token = tokenStatus(session);

  useEffect(() => {
    void loadProfile();
  }, [loadProfile]);

  useEffect(() => {
    if (!session?.accessToken || !session.subject) return;
    let cancelled = false;
    (async () => {
      try {
        const envelope = await rbacAuthApi.listSessions(
          session.accessToken,
          session.subject,
        );
        if (cancelled) return;
        if (envelope.ok && Array.isArray(envelope.result)) {
          setSessions(envelope.result);
          setSessionsError(null);
        } else {
          setSessions([]);
          setSessionsError(
            envelope.message ||
              "Data unavailable. Session list endpoint not available.",
          );
        }
      } catch {
        if (!cancelled) {
          setSessions([]);
          setSessionsError(
            "Data unavailable. Active session listing requires admin sessions API.",
          );
        }
      }
      try {
        const [profileEnv, devicesEnv, historyEnv] = await Promise.all([
          enterpriseAuthApi.getProfile(session.accessToken),
          enterpriseAuthApi.listDevices(session.accessToken),
          enterpriseAuthApi.myLoginHistory(session.accessToken),
        ]);
        if (cancelled) return;
        if (profileEnv.result) {
          const links = (profileEnv.result.linkedProviders ||
            profileEnv.result.linked_providers ||
            []) as Record<string, unknown>[];
          setLinked(Array.isArray(links) ? links : []);
          setNewName(String(profileEnv.result.name || user?.displayName || ""));
          setNewEmail(String(profileEnv.result.email || user?.email || ""));
        }
        setDevices(
          Array.isArray(devicesEnv.result) ? devicesEnv.result : [],
        );
        setHistory(
          Array.isArray(historyEnv.result) ? historyEnv.result : [],
        );
      } catch {
        /* profile extras optional when enterprise API offline */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [session?.accessToken, session?.subject, user?.displayName, user?.email]);

  if (!user || !session) {
    return (
      <EmptyState
        title="Profile unavailable"
        description="No active session. Sign in to view your profile."
        action={
          <Link href="/login">
            <Button>Sign in</Button>
          </Link>
        }
      />
    );
  }

  const initials = user.displayName.slice(0, 2).toUpperCase();

  return (
    <PageLayout
      title="Profile"
      description="Account summary, roles, permissions, and session status."
      actions={
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await refreshSession();
              } finally {
                setBusy(false);
              }
            }}
          >
            Refresh token
          </Button>
          <Button
            variant="danger"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await logout();
                router.push("/login");
              } finally {
                setBusy(false);
              }
            }}
          >
            Sign out
          </Button>
        </div>
      }
    >
      <Stack gap={6}>
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Avatar>
                <AvatarFallback>{initials}</AvatarFallback>
              </Avatar>
              <div>
                <CardTitle>{user.displayName}</CardTitle>
                <CardDescription>
                  {user.email || "Data unavailable."}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <Row label="Username" value={user.username} />
              <Row label="Subject" value={user.subject} />
              <Row label="Primary role" value={user.role} />
              <Row
                label="Auth status"
                value={sessionStatusLabel(status)}
              />
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Roles</CardTitle>
            <CardDescription>Assigned institutional roles</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {user.roles.length ? (
              user.roles.map((role) => (
                <Badge key={role} variant="outline">
                  {role}
                </Badge>
              ))
            ) : (
              <EmptyState title="Data unavailable." className="py-4" />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Permissions</CardTitle>
            <CardDescription>Effective permission set</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {user.permissions.length ? (
              user.permissions.map((permission) => (
                <Badge key={permission}>{permission}</Badge>
              ))
            ) : (
              <EmptyState
                title="Data unavailable."
                description="Permissions populate after RBAC evaluate succeeds."
                className="py-4"
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Session & token</CardTitle>
            <CardDescription>Current authentication session</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <Row label="Session id" value={session.sessionId || "Data unavailable."} />
              <Row label="Auth method" value={session.authMethod} />
              <Row label="Issued at" value={session.issuedAt} />
              <Row label="Expires at" value={session.expiresAt || "—"} />
              <Row label="Token status" value={token.label} />
              <Row
                label="Refresh token"
                value={token.hasRefresh ? "Present" : "Data unavailable."}
              />
              <Row
                label="Remember me"
                value={session.rememberMe ? "Yes" : "No"}
              />
              <Row
                label="Frontend foundation"
                value={`v${env.foundationVersion}`}
              />
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Active sessions</CardTitle>
            <CardDescription>
              Current device session. Logout-all requires backend support.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {sessions === null ? (
              <Skeleton className="h-24 w-full" />
            ) : sessionsError ? (
              <Alert variant="info" title="Session listing">
                {sessionsError}
              </Alert>
            ) : sessions.length === 0 ? (
              <EmptyState
                title="Data unavailable."
                description="No remote sessions returned for this user."
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Session</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.map((row) => (
                    <TableRow key={row.session_id}>
                      <TableCell className="font-mono text-xs">
                        {row.session_id}
                        {row.session_id === session.sessionId ? " (current)" : ""}
                      </TableCell>
                      <TableCell className="text-xs">{row.created_at}</TableCell>
                      <TableCell className="text-xs">{row.expires_at}</TableCell>
                      <TableCell>
                        {row.revoked ? (
                          <Badge variant="danger">Revoked</Badge>
                        ) : (
                          <Badge variant="outline">Active</Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
            <div className="mt-4 flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={async () => {
                  await logout();
                  router.push("/login");
                }}
              >
                Logout current session
              </Button>
              <Button
                variant="outline"
                disabled={busy || !session.accessToken}
                onClick={async () => {
                  if (!session.accessToken) return;
                  setBusy(true);
                  try {
                    await enterpriseAuthApi.revokeMySessions(session.accessToken);
                    await logout();
                    router.push("/login");
                  } catch {
                    setAccountErr("Unable to revoke all sessions.");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Logout all sessions
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Account security</CardTitle>
            <CardDescription>
              Profile, password, email, linked providers, and trusted devices.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {accountMsg ? (
              <Alert variant="info" title="Account">
                {accountMsg}
              </Alert>
            ) : null}
            {accountErr ? (
              <ValidationMessage tone="error">{accountErr}</ValidationMessage>
            ) : null}
            <FormField label="Display name" htmlFor="profile-name">
              <Input
                id="profile-name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </FormField>
            <Button
              size="sm"
              disabled={busy}
              onClick={async () => {
                if (!session.accessToken) return;
                setBusy(true);
                setAccountErr(null);
                try {
                  await enterpriseAuthApi.updateProfile(
                    { name: newName },
                    session.accessToken,
                  );
                  setAccountMsg("Profile updated.");
                  await loadProfile();
                } catch (e) {
                  setAccountErr(e instanceof Error ? e.message : "Update failed");
                } finally {
                  setBusy(false);
                }
              }}
            >
              Save name
            </Button>
            <FormField label="Change email" htmlFor="profile-email">
              <Input
                id="profile-email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
              />
            </FormField>
            <Button
              size="sm"
              variant="secondary"
              disabled={busy}
              onClick={async () => {
                if (!session.accessToken) return;
                setBusy(true);
                setAccountErr(null);
                try {
                  const envl = await enterpriseAuthApi.changeEmail(
                    newEmail,
                    session.accessToken,
                  );
                  setAccountMsg(
                    String(
                      (envl.result as { message?: string })?.message ||
                        "Verification sent to the new email.",
                    ),
                  );
                } catch (e) {
                  setAccountErr(e instanceof Error ? e.message : "Email change failed");
                } finally {
                  setBusy(false);
                }
              }}
            >
              Request email change
            </Button>
            <FormField label="Current password" htmlFor="profile-cur-pw">
              <PasswordInput
                id="profile-cur-pw"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </FormField>
            <FormField label="New password" htmlFor="profile-new-pw">
              <PasswordInput
                id="profile-new-pw"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </FormField>
            <Button
              size="sm"
              variant="secondary"
              disabled={busy}
              onClick={async () => {
                if (!session.accessToken) return;
                setBusy(true);
                setAccountErr(null);
                try {
                  await enterpriseAuthApi.changePassword(
                    {
                      current_password: currentPassword,
                      new_password: newPassword,
                    },
                    session.accessToken,
                  );
                  setAccountMsg("Password changed.");
                  setCurrentPassword("");
                  setNewPassword("");
                } catch (e) {
                  setAccountErr(
                    e instanceof Error ? e.message : "Password change failed",
                  );
                } finally {
                  setBusy(false);
                }
              }}
            >
              Change password
            </Button>
            <div>
              <p className="mb-2 text-sm text-[var(--muted)]">Linked providers</p>
              {linked.length === 0 ? (
                <p className="text-sm">No linked OAuth providers.</p>
              ) : (
                <ul className="space-y-2">
                  {linked.map((lnk) => (
                    <li
                      key={String(lnk.provider)}
                      className="flex items-center justify-between gap-2 text-sm"
                    >
                      <span>{String(lnk.provider)}</span>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={async () => {
                          if (!session.accessToken) return;
                          try {
                            await enterpriseAuthApi.unlinkProvider(
                              String(lnk.provider),
                              session.accessToken,
                            );
                            setLinked((prev) =>
                              prev.filter(
                                (p) => p.provider !== lnk.provider,
                              ),
                            );
                          } catch (e) {
                            setAccountErr(
                              e instanceof Error
                                ? e.message
                                : "Unlink failed",
                            );
                          }
                        }}
                      >
                        Unlink
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <p className="mb-2 text-sm text-[var(--muted)]">Devices</p>
              {devices.length === 0 ? (
                <p className="text-sm">No devices registered yet.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Label</TableHead>
                      <TableHead>Trusted</TableHead>
                      <TableHead />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {devices.map((d) => (
                      <TableRow key={String(d.device_id)}>
                        <TableCell className="text-xs">
                          {String(d.label || d.device_id)}
                        </TableCell>
                        <TableCell>{String(Boolean(d.trusted))}</TableCell>
                        <TableCell className="space-x-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={async () => {
                              if (!session.accessToken) return;
                              await enterpriseAuthApi.trustDevice(
                                String(d.device_id),
                                !d.trusted,
                                session.accessToken,
                              );
                              const refreshed =
                                await enterpriseAuthApi.listDevices(
                                  session.accessToken,
                                );
                              setDevices(
                                Array.isArray(refreshed.result)
                                  ? refreshed.result
                                  : [],
                              );
                            }}
                          >
                            {d.trusted ? "Untrust" : "Trust"}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={async () => {
                              if (!session.accessToken) return;
                              await enterpriseAuthApi.revokeDevice(
                                String(d.device_id),
                                session.accessToken,
                              );
                              setDevices((prev) =>
                                prev.filter(
                                  (x) => x.device_id !== d.device_id,
                                ),
                              );
                            }}
                          >
                            Revoke
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
            <div>
              <p className="mb-2 text-sm text-[var(--muted)]">Login history</p>
              {history.length === 0 ? (
                <p className="text-sm">No login history.</p>
              ) : (
                <ul className="max-h-40 space-y-1 overflow-auto text-xs">
                  {history.slice(0, 20).map((h) => (
                    <li key={String(h.entry_id)}>
                      {String(h.created_at)} · {String(h.provider)} ·{" "}
                      {h.success ? "ok" : "fail"}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <Button
              variant="danger"
              disabled={busy}
              onClick={async () => {
                if (!session.accessToken) return;
                if (
                  !window.confirm(
                    "Disable your account and revoke sessions? This cannot be undone from the UI.",
                  )
                ) {
                  return;
                }
                setBusy(true);
                try {
                  await enterpriseAuthApi.deleteAccount(session.accessToken);
                  await logout();
                  router.push("/login");
                } catch (e) {
                  setAccountErr(
                    e instanceof Error ? e.message : "Delete failed",
                  );
                } finally {
                  setBusy(false);
                }
              }}
            >
              Delete account
            </Button>
          </CardContent>
        </Card>
      </Stack>
    </PageLayout>
  );
}

export function UserProfile() {
  return (
    <AuthGuard>
      <ProfileContent />
    </AuthGuard>
  );
}

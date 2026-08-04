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
  PageLayout,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ds";
import { AuthGuard } from "@/components/auth/ProtectedRoute";
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
    })();
    return () => {
      cancelled = true;
    };
  }, [session?.accessToken, session?.subject]);

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
              <Button variant="outline" disabled title="Data unavailable.">
                Logout all sessions
              </Button>
            </div>
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

"use client";

import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { useAuth } from "@/lib/auth/AuthProvider";
import { sessionStatusLabel } from "@/lib/auth/types";
import { env } from "@/lib/env";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:items-center sm:justify-between">
      <dt className="text-[var(--muted)]">{label}</dt>
      <dd className="font-mono text-sm break-all">{value}</dd>
    </div>
  );
}

function ProfileContent() {
  const { user, session, status, logout } = useAuth();

  if (!user || !session) {
    return (
      <Alert tone="warning" title="Profile unavailable">
        No active session. Sign in to view your profile.
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader title="User Profile" description="Session identity" />
        <CardBody>
          <dl className="space-y-3 text-sm">
            <Row label="Display Name" value={user.displayName} />
            <Row
              label="Email"
              value={user.email ?? "Not available (placeholder)"}
            />
            <Row label="Role" value={user.role} />
            <Row label="Username" value={user.username} />
            <Row label="Subject" value={user.subject} />
          </dl>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Session" description="Current authentication state" />
        <CardBody>
          <dl className="space-y-3 text-sm">
            <Row label="Session Status" value={sessionStatusLabel(status)} />
            <Row label="Auth Method" value={session.authMethod} />
            <Row label="Issued At" value={session.issuedAt} />
            <Row label="Expires At" value={session.expiresAt ?? "—"} />
            <Row label="Remember Me" value={session.rememberMe ? "Yes" : "No"} />
            <Row label="Frontend Version" value={`v${env.frontendVersion}`} />
          </dl>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                logout();
                window.location.href = "/login";
              }}
            >
              Sign out
            </Button>
            <Link href="/diagnostics">
              <Button variant="secondary">Diagnostics</Button>
            </Link>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}

export function UserProfile() {
  return (
    <ProtectedRoute>
      <ProfileContent />
    </ProtectedRoute>
  );
}

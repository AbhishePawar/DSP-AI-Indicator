"use client";

import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { useAuth } from "@/lib/auth/AuthProvider";
import { usePersistence } from "@/providers/PersistenceProvider";
import { SyncStatusBadge } from "./SyncStatusBadge";

export function PortfolioSync() {
  const { status: authStatus } = useAuth();
  const { syncStatus, lastSyncedAt, lastError, syncNow, bundle } =
    usePersistence();

  if (authStatus !== "authenticated") {
    return (
      <Card>
        <CardHeader title="Portfolio Sync" description="Sign in to persist" />
        <CardBody className="text-sm text-[var(--muted)]">
          Portfolio data is in-memory until you sign in. Local cache syncs
          automatically when authenticated.
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title="Portfolio Sync"
        description={bundle?.portfolio.name ?? "My Portfolio"}
      />
      <CardBody className="space-y-3 text-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <SyncStatusBadge status={syncStatus} lastSyncedAt={lastSyncedAt} />
          <Button size="sm" variant="secondary" onClick={() => void syncNow()}>
            Sync now
          </Button>
        </div>
        {lastError ? (
          <p className="text-[var(--danger-fg)]">{lastError}</p>
        ) : (
          <p className="text-[var(--muted)]">
            Holdings, allocations, and activity timeline persist for your
            account in this browser.
          </p>
        )}
        <Link href="/profile">
          <Button size="sm" variant="ghost">
            View profile
          </Button>
        </Link>
      </CardBody>
    </Card>
  );
}

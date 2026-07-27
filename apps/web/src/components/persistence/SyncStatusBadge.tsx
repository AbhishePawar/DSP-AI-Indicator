"use client";

import { Badge } from "@/components/ui/Badge";
import type { SyncStatus } from "@/lib/persistence/types";

const LABELS: Record<SyncStatus, string> = {
  idle: "Idle",
  loading: "Loading",
  saving: "Saving",
  saved: "Saved",
  error: "Sync error",
  conflict: "Conflict",
};

const TONES: Record<
  SyncStatus,
  "neutral" | "success" | "warning" | "danger" | "accent"
> = {
  idle: "neutral",
  loading: "accent",
  saving: "accent",
  saved: "success",
  error: "danger",
  conflict: "warning",
};

export function SyncStatusBadge({
  status,
  lastSyncedAt,
}: {
  status: SyncStatus;
  lastSyncedAt?: string | null;
}) {
  return (
    <span
      className="inline-flex items-center gap-2"
      title={
        lastSyncedAt
          ? `Last synced ${new Date(lastSyncedAt).toLocaleString()}`
          : undefined
      }
    >
      <Badge tone={TONES[status]}>{LABELS[status]}</Badge>
      {lastSyncedAt && status === "saved" ? (
        <span className="hidden font-mono text-[10px] text-[var(--muted)] xl:inline">
          {new Date(lastSyncedAt).toLocaleTimeString()}
        </span>
      ) : null}
    </span>
  );
}

"use client";

import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Spinner,
} from "@/components/ds";
import { api } from "@/lib/api/client";
import type { ProviderAuditLog, ProviderRecord } from "@/lib/api/providerTypes";

export type ProviderAuditModalProps = {
  provider: ProviderRecord | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  token?: string | null;
};

export function ProviderAuditModal({
  provider,
  open,
  onOpenChange,
  token,
}: ProviderAuditModalProps) {
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<ProviderAuditLog[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !provider) return;

    let active = true;
    setLoading(true);
    setError(null);

    api
      .adminGetProviderAudit(provider.provider_id, { token })
      .then((res) => {
        if (active) {
          setLogs(res.audit_log || []);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load audit history.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [open, provider, token]);

  if (!provider) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Audit Trail — {provider.display_name}</DialogTitle>
          <DialogDescription>
            Historical record of configuration updates, credential rotations, and health transitions for {provider.provider_id}.
          </DialogDescription>
        </DialogHeader>

        <div className="py-2 max-h-[26rem] overflow-y-auto space-y-3">
          {loading ? (
            <div className="flex items-center justify-center p-8 text-sm text-[var(--muted)]">
              <Spinner className="mr-2 h-4 w-4" />
              Loading audit logs...
            </div>
          ) : null}

          {error ? (
            <p className="text-sm text-[var(--danger-fg)]">{error}</p>
          ) : null}

          {!loading && !error && logs.length === 0 ? (
            <p className="text-sm text-[var(--muted)] text-center py-6">
              No audit records recorded yet for this provider.
            </p>
          ) : null}

          {!loading && logs.length > 0 ? (
            <div className="space-y-2">
              {logs.map((log, idx) => (
                <div
                  key={idx}
                  className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-3 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-[var(--fg)]">{log.action}</span>
                    <Badge variant="outline">v{log.version}</Badge>
                  </div>
                  <div className="flex items-center gap-4 text-[var(--muted)]">
                    <span>Author: {log.author || "system"}</span>
                    <span>{new Date(log.timestamp).toLocaleString()}</span>
                  </div>
                  {log.details && Object.keys(log.details).length > 0 ? (
                    <pre className="mt-1 font-mono text-[11px] text-[var(--muted)] overflow-x-auto bg-[var(--surface)] p-2 rounded">
                      {JSON.stringify(log.details, null, 2)}
                    </pre>
                  ) : null}
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

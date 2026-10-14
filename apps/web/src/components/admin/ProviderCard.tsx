"use client";

import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Spinner,
  Switch,
} from "@/components/ds";
import { api } from "@/lib/api/client";
import type {
  ConnectionTestResponse,
  ProviderHealthStatus,
  ProviderRecord,
} from "@/lib/api/providerTypes";

export type ProviderCardProps = {
  provider: ProviderRecord;
  token?: string | null;
  onRefresh: () => void;
  onOpenCredentialModal: (provider: ProviderRecord) => void;
  onOpenAuditModal: (provider: ProviderRecord) => void;
};

export function ProviderCard({
  provider,
  token,
  onRefresh,
  onOpenCredentialModal,
  onOpenAuditModal,
}: ProviderCardProps) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<ConnectionTestResponse | null>(null);
  const [updatingModel, setUpdatingModel] = useState(false);
  const [togglingStatus, setTogglingStatus] = useState(false);
  const [rollingBack, setRollingBack] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const getHealthBadge = (status: ProviderHealthStatus) => {
    switch (status) {
      case "healthy":
        return <Badge variant="accent">Connection Verified</Badge>;
      case "configured_untested":
        return <Badge variant="warning">Configured, Not Tested</Badge>;
      case "rate_limited":
      case "quota_exhausted":
        return <Badge variant="warning">{status === "rate_limited" ? "Rate Limited" : "Quota Exhausted"}</Badge>;
      case "provider_outage":
      case "timeout":
      case "network_error":
        return <Badge variant="warning">Temporarily Unavailable</Badge>;
      case "auth_failure":
      case "expired_token":
      case "permission_failure":
      case "config_error":
      case "error":
      case "unreachable":
        return <Badge variant="danger">Connection Failed</Badge>;
      case "unsupported":
        return <Badge variant="outline">Unsupported</Badge>;
      case "not_configured":
      default:
        return <Badge variant="outline">Not Configured</Badge>;
    }
  };

  const handleToggleStatus = async (checked: boolean) => {
    setTogglingStatus(true);
    setActionError(null);
    try {
      await api.adminUpdateProviderStatus(
        provider.provider_id,
        { is_active: checked },
        { token },
      );
      onRefresh();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to toggle status.");
    } finally {
      setTogglingStatus(false);
    }
  };

  const handleModelChange = async (newModel: string) => {
    if (newModel === provider.selected_model) return;
    setUpdatingModel(true);
    setActionError(null);
    try {
      await api.adminUpdateProviderModel(
        provider.provider_id,
        { model: newModel },
        { token },
      );
      onRefresh();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to update model.");
    } finally {
      setUpdatingModel(false);
    }
  };

  const handleQuickTest = async () => {
    setTesting(true);
    setActionError(null);
    setTestResult(null);
    try {
      const res = await api.adminTestProvider(
        provider.provider_id,
        undefined,
        { token },
      );
      setTestResult(res);
      onRefresh();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Test failed.");
    } finally {
      setTesting(false);
    }
  };

  const handleRevoke = async () => {
    if (!provider.has_credential) return;
    const confirmed = typeof window !== "undefined" && window.confirm(
      `Revoke the stored credential for ${provider.display_name}? This cannot be undone.`
    );
    if (!confirmed) return;

    setActionError(null);
    try {
      await api.adminRevokeProviderCredential(provider.provider_id, { token });
      onRefresh();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to revoke credential.");
    }
  };

  const handleRollback = async () => {
    if (provider.version <= 1) return;
    if (typeof window !== "undefined" && !window.confirm(`Roll back ${provider.display_name} to previous configuration snapshot?`)) {
      return;
    }
    setRollingBack(true);
    setActionError(null);
    try {
      await api.adminRollbackProvider(provider.provider_id, { token });
      onRefresh();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Rollback failed.");
    } finally {
      setRollingBack(false);
    }
  };

  return (
    <Card className="flex flex-col justify-between border-[var(--border)] bg-[var(--surface)] shadow-sm hover:border-[var(--accent)] transition-all">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <CardTitle className="text-base font-semibold">{provider.display_name}</CardTitle>
              <Badge variant="outline" className="text-[10px] uppercase font-mono">
                {provider.provider_id}
              </Badge>
            </div>
            <CardDescription className="text-xs text-[var(--muted)] mt-0.5">
              {provider.category === "ai" ? "Generative Intelligence Model" : "Financial Market Data Provider"}
            </CardDescription>
          </div>

          <div className="flex items-center gap-2">
            {getHealthBadge(provider.health_status)}
            <div className="flex items-center gap-1.5 ml-1" title={provider.is_active ? "Provider is Active" : "Provider is Inactive"}>
              <Switch
                checked={provider.is_active}
                disabled={togglingStatus}
                onCheckedChange={handleToggleStatus}
                aria-label={`Toggle active state for ${provider.display_name}`}
              />
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3 text-xs">
        {/* Model selection */}
        <div>
          <span className="block text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider mb-1">
            Active Model
          </span>
          {provider.available_models && provider.available_models.length > 1 ? (
            <Select
              value={provider.selected_model}
              disabled={updatingModel}
              onValueChange={handleModelChange}
            >
              <SelectTrigger className="h-8 text-xs w-full bg-[var(--surface-2)]">
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent>
                {provider.available_models.map((m) => (
                  <SelectItem key={m} value={m} className="text-xs">
                    {m}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <div className="font-mono text-xs text-[var(--fg)] bg-[var(--surface-2)] px-2.5 py-1.5 rounded border border-[var(--border)]">
              {provider.selected_model || "Default"}
            </div>
          )}
        </div>

        {/* Credentials & Health Overview */}
        <div className="grid grid-cols-2 gap-2 pt-1 border-t border-[var(--border)]">
          <div>
            <span className="text-[11px] text-[var(--muted)] block">Credential</span>
            {provider.has_credential ? (
              <span className="inline-flex flex-col text-xs font-medium text-emerald-600 dark:text-emerald-400">
                <span>● Key Configured</span>
                {provider.masked_credential ? <span className="font-mono text-[10px] text-[var(--muted)]">{provider.masked_credential}</span> : null}
              </span>
            ) : (
              <span className="inline-flex items-center text-xs font-medium text-amber-600 dark:text-amber-400">
                ○ Missing Key
              </span>
            )}
          </div>

          <div>
            <span className="text-[11px] text-[var(--muted)] block">Last test</span>
            <span className="text-[10px] text-[var(--fg)]">
              {provider.last_tested_at ? new Date(provider.last_tested_at).toLocaleString() : "Never tested"}
            </span>
          </div>
          <div>
            <span className="text-[11px] text-[var(--muted)] block">Latency</span>
            <span className="font-mono text-xs text-[var(--fg)]">
              {provider.last_latency_ms != null ? `${provider.last_latency_ms} ms` : "--"}
            </span>
          </div>
        </div>

        {/* Capabilities */}
        <div>
          <span className="text-[11px] text-[var(--muted)] block mb-1">Capabilities</span>
          <div className="flex flex-wrap gap-1">
            {provider.supported_capabilities?.map((cap) => (
              <span
                key={cap}
                className="rounded bg-[var(--surface-2)] px-1.5 py-0.5 text-[10px] text-[var(--muted)] border border-[var(--border)]"
              >
                {cap}
              </span>
            ))}
          </div>
        </div>

        {provider.error_message ? (
          <p className="text-[11px] text-[var(--danger-fg)]" role="status">{provider.error_message}</p>
        ) : null}

        {/* Dynamic Test or Action Feedback */}
        {testResult ? (
          <div
            className={`p-2 rounded text-[11px] border ${
              testResult.success
                ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 text-emerald-800 dark:text-emerald-200"
                : "bg-red-50 dark:bg-red-950/40 border-red-300 text-red-800 dark:text-red-200"
            }`}
          >
            <div className="flex justify-between font-semibold">
              <span>{testResult.success ? "Test Passed" : "Test Failed"}</span>
              <span>{testResult.latency_ms} ms</span>
            </div>
            {testResult.sanitized_error ? (
              <p className="mt-0.5 text-[10px]">{testResult.sanitized_error}</p>
            ) : null}
          </div>
        ) : null}

        {actionError ? (
          <p className="text-[11px] text-[var(--danger-fg)]">{actionError}</p>
        ) : null}
      </CardContent>

      <CardFooter className="flex items-center justify-between gap-1.5 border-t border-[var(--border)] pt-3 bg-[var(--surface-2)]/50 rounded-b-lg">
        <div className="flex items-center gap-1.5">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 text-xs px-2.5"
            onClick={handleQuickTest}
            disabled={testing || !provider.has_credential}
            title={!provider.has_credential ? "Configure API key first" : "Run connection test"}
          >
            {testing ? <Spinner className="h-3 w-3 mr-1" /> : null}
            Test
          </Button>

          <Button
            type="button"
            variant="primary"
            size="sm"
            className="h-7 text-xs px-2.5"
            onClick={() => onOpenCredentialModal(provider)}
          >
            {provider.has_credential ? "Replace Key" : "Add Key"}
          </Button>
          {provider.has_credential ? (
            <Button type="button" variant="ghost" size="sm" className="h-7 text-xs px-2" onClick={handleRevoke}>
              Revoke
            </Button>
          ) : null}
        </div>

        <div className="flex items-center gap-1">
          {provider.version > 1 ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 text-xs px-2 text-[var(--muted)] hover:text-[var(--fg)]"
              onClick={handleRollback}
              disabled={rollingBack}
              title={`Roll back to previous snapshot (currently v${provider.version})`}
            >
              Rollback
            </Button>
          ) : null}

          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-7 text-xs px-2 text-[var(--muted)] hover:text-[var(--fg)]"
            onClick={() => onOpenAuditModal(provider)}
            title="View audit trail"
          >
            Audit
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}

"use client";

/**
 * RC1 Milestone 11 — Super Admin Control Center shell.
 * Thin /api/v1/admin/* client — configuration overlays only; no engine logic.
 */

import { Suspense, lazy, useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Alert, Button, Input } from "@/components/ds";
import { PageHeader } from "@/components/layout/PageHeader";
import { SurfaceTrustChrome } from "@/components/trust/SurfaceTrustChrome";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { featureFlags } from "@/lib/featureFlags";
import { dashboardSurfaceTrust } from "@/lib/trust/surfaceTrust";

const LazyJsonPanel = lazy(() =>
  import("./ControlCenterPanels").then((m) => ({
    default: m.ControlCenterJsonPanel,
  })),
);

type Tab =
  | "overview"
  | "registry"
  | "branding"
  | "flags"
  | "ai"
  | "valuation"
  | "rules"
  | "security"
  | "history"
  | "monitoring"
  | "audit";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "registry", label: "Registry" },
  { id: "branding", label: "Branding" },
  { id: "flags", label: "Feature flags" },
  { id: "ai", label: "AI" },
  { id: "valuation", label: "Valuation" },
  { id: "rules", label: "Business rules" },
  { id: "security", label: "Security" },
  { id: "history", label: "History / Rollback" },
  { id: "monitoring", label: "Monitoring" },
  { id: "audit", label: "Audit" },
];

export function ControlCenter() {
  const { session, user } = useAuth();
  const token = session?.accessToken;
  const actorId =
    (user as { id?: string } | null)?.id ||
    (user as { email?: string } | null)?.email ||
    "admin";
  const opts = useMemo(() => ({ token }), [token]);
  const qc = useQueryClient();

  const [tab, setTab] = useState<Tab>("overview");
  const [filter, setFilter] = useState("");
  const [moduleId, setModuleId] = useState("branding");
  const [reason, setReason] = useState("");
  const [jsonPatch, setJsonPatch] = useState('{\n  "theme": "system"\n}');
  const [flagKey, setFlagKey] = useState("copilot");
  const [flagEnabled, setFlagEnabled] = useState(true);
  const [ruleName, setRuleName] = useState("mos-alert");
  const [rollbackVersion, setRollbackVersion] = useState("");
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const enabled = featureFlags.controlCenter;

  const dashQuery = useQuery({
    queryKey: ["cc-dashboard"],
    queryFn: () => api.controlCenterDashboard(opts),
    enabled,
    retry: false,
  });

  const registryQuery = useQuery({
    queryKey: ["cc-registry"],
    queryFn: () => api.controlCenterRegistry(undefined, opts),
    enabled: enabled && (tab === "registry" || tab === "overview"),
    retry: false,
  });

  const historyQuery = useQuery({
    queryKey: ["cc-history"],
    queryFn: () => api.controlCenterHistory({ limit: 50 }, opts),
    enabled: enabled && (tab === "history" || tab === "audit"),
    retry: false,
  });

  const rulesQuery = useQuery({
    queryKey: ["cc-rules"],
    queryFn: () => api.controlCenterBusinessRules(opts),
    enabled: enabled && tab === "rules",
    retry: false,
  });

  const monitoringQuery = useQuery({
    queryKey: ["cc-monitoring"],
    queryFn: () => api.controlCenterMonitoring(opts),
    enabled: enabled && tab === "monitoring",
    retry: false,
  });

  const auditQuery = useQuery({
    queryKey: ["cc-audit"],
    queryFn: () => api.controlCenterAudit(opts),
    enabled: enabled && tab === "audit",
    retry: false,
  });

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ["cc-dashboard"] });
    void qc.invalidateQueries({ queryKey: ["cc-registry"] });
    void qc.invalidateQueries({ queryKey: ["cc-history"] });
    void qc.invalidateQueries({ queryKey: ["cc-rules"] });
  };

  const updateMut = useMutation({
    mutationFn: () => {
      let configuration: Record<string, unknown> = {};
      try {
        configuration = JSON.parse(jsonPatch) as Record<string, unknown>;
      } catch {
        throw new Error("Invalid JSON patch");
      }
      return api.controlCenterUpdateConfiguration(
        {
          module_id: moduleId,
          configuration,
          reason: reason || "control center update",
          author: actorId,
        },
        opts,
      );
    },
    onSuccess: (res) => {
      setStatusMsg(res.ok ? "Configuration updated." : res.message || "Data unavailable.");
      invalidate();
    },
    onError: (err: Error) => setStatusMsg(err.message || "Data unavailable."),
  });

  const brandingMut = useMutation({
    mutationFn: () => {
      let configuration: Record<string, unknown> = {};
      try {
        configuration = JSON.parse(jsonPatch) as Record<string, unknown>;
      } catch {
        throw new Error("Invalid JSON patch");
      }
      return api.controlCenterBranding(
        { configuration, reason: reason || "branding update", author: actorId },
        opts,
      );
    },
    onSuccess: (res) => {
      setStatusMsg(res.ok ? "Branding updated." : res.message || "Data unavailable.");
      invalidate();
    },
    onError: (err: Error) => setStatusMsg(err.message || "Data unavailable."),
  });

  const flagsMut = useMutation({
    mutationFn: () =>
      api.controlCenterFeatureFlags(
        {
          flag: flagKey,
          enabled: flagEnabled,
          reason: reason || "feature flag update",
          author: actorId,
        },
        opts,
      ),
    onSuccess: (res) => {
      setStatusMsg(res.ok ? "Feature flag updated." : res.message || "Data unavailable.");
      invalidate();
    },
    onError: (err: Error) => setStatusMsg(err.message || "Data unavailable."),
  });

  const valuationMut = useMutation({
    mutationFn: () => {
      let configuration: Record<string, unknown> = {};
      try {
        configuration = JSON.parse(jsonPatch) as Record<string, unknown>;
      } catch {
        throw new Error("Invalid JSON patch");
      }
      return api.controlCenterValuation(
        {
          configuration,
          reason: reason || "valuation overlay update",
          author: actorId,
        },
        opts,
      );
    },
    onSuccess: (res) => {
      setStatusMsg(
        res.ok
          ? "Valuation config overlay saved (engines not executed)."
          : res.message || "Data unavailable.",
      );
      invalidate();
    },
    onError: (err: Error) => setStatusMsg(err.message || "Data unavailable."),
  });

  const aiMut = useMutation({
    mutationFn: () => {
      let configuration: Record<string, unknown> = {};
      try {
        configuration = JSON.parse(jsonPatch) as Record<string, unknown>;
      } catch {
        throw new Error("Invalid JSON patch");
      }
      return api.controlCenterAi(
        { configuration, reason: reason || "ai config update", author: actorId },
        opts,
      );
    },
    onSuccess: (res) => {
      setStatusMsg(res.ok ? "AI config overlay saved." : res.message || "Data unavailable.");
      invalidate();
    },
    onError: (err: Error) => setStatusMsg(err.message || "Data unavailable."),
  });

  const ruleMut = useMutation({
    mutationFn: () =>
      api.controlCenterUpsertBusinessRule(
        {
          name: ruleName,
          enabled: true,
          category: "alerts",
          condition: { type: "threshold" },
          action: { type: "notify" },
          reason: reason || "business rule upsert",
          author: actorId,
        },
        opts,
      ),
    onSuccess: (res) => {
      setStatusMsg(res.ok ? "Business rule saved." : res.message || "Data unavailable.");
      invalidate();
    },
    onError: (err: Error) => setStatusMsg(err.message || "Data unavailable."),
  });

  const securityMut = useMutation({
    mutationFn: () => {
      let configuration: Record<string, unknown> = {};
      try {
        configuration = JSON.parse(jsonPatch) as Record<string, unknown>;
      } catch {
        throw new Error("Invalid JSON patch");
      }
      return api.controlCenterSecurity(
        {
          configuration,
          reason: reason || "security config update",
          author: actorId,
        },
        opts,
      );
    },
    onSuccess: (res) => {
      setStatusMsg(res.ok ? "Security config updated." : res.message || "Data unavailable.");
      invalidate();
    },
    onError: (err: Error) => setStatusMsg(err.message || "Data unavailable."),
  });

  const rollbackMut = useMutation({
    mutationFn: () =>
      api.controlCenterRollback(
        {
          version: Number(rollbackVersion),
          reason: reason || "one-click rollback",
          author: actorId,
        },
        opts,
      ),
    onSuccess: (res) => {
      setStatusMsg(res.ok ? "Rollback applied." : res.message || "Data unavailable.");
      invalidate();
    },
    onError: (err: Error) => setStatusMsg(err.message || "Data unavailable."),
  });

  const modules = Object.keys(
    ((registryQuery.data?.result as { modules?: Record<string, unknown> } | undefined)
      ?.modules || {}) as Record<string, unknown>,
  ).filter((m) => !filter || m.includes(filter.toLowerCase()));

  const filteredTabs = TABS.filter(
    (t) => !filter || t.label.toLowerCase().includes(filter.toLowerCase()),
  );

  const trustSummary = useMemo(
    () =>
      dashboardSurfaceTrust({
        widgetCount: modules.length || TABS.length,
        note: "Super Admin Control Center · config overlays · no engine execution",
      }),
    [modules.length],
  );

  if (!enabled) {
    return (
      <div className="space-y-4 p-6">
        <Alert variant="warning" title="Control Center disabled.">
          Set NEXT_PUBLIC_CONTROL_CENTER=true to enable.
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-6" data-testid="control-center">
      <SurfaceTrustChrome summary={trustSummary} />
      <PageHeader
        title="Super Admin Control Center"
        description="Platform operating system — configuration registry, branding, flags, rules, and façades over Admin / SaaS / Ops. Thin client over /api/v1/admin. No engine execution in the browser."
      />

      <div className="flex flex-wrap items-center gap-3">
        <Input
          aria-label="Search modules and tabs"
          placeholder="Search…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="max-w-xs"
        />
        <Link
          href="/ops"
          className="text-sm text-[var(--dsp-accent)] underline-offset-2 hover:underline"
        >
          Production Ops
        </Link>
        <Link
          href="/saas"
          className="text-sm text-[var(--dsp-accent)] underline-offset-2 hover:underline"
        >
          SaaS Platform
        </Link>
        <Link
          href="/admin"
          className="text-sm text-[var(--dsp-accent)] underline-offset-2 hover:underline"
        >
          Enterprise Admin
        </Link>
      </div>

      {statusMsg ? (
        <Alert variant="info" title="Status">
          {statusMsg}
        </Alert>
      ) : null}

      <div
        role="tablist"
        aria-label="Control Center sections"
        className="flex flex-wrap gap-2 border-b border-[var(--dsp-border)] pb-2"
      >
        {filteredTabs.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={
              tab === t.id
                ? "rounded-md bg-[var(--dsp-accent)] px-3 py-1.5 text-sm text-white"
                : "rounded-md px-3 py-1.5 text-sm text-[var(--dsp-text-muted)] hover:bg-[var(--dsp-surface)]"
            }
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div role="tabpanel" className="space-y-4">
        {tab === "overview" ? (
          <Suspense fallback={<p>Loading overview…</p>}>
            <LazyJsonPanel
              title="Control Center overview"
              data={dashQuery.data?.result}
              loading={dashQuery.isLoading}
              error={dashQuery.error ? "Data unavailable." : null}
            />
          </Suspense>
        ) : null}

        {tab === "registry" ? (
          <div className="space-y-3">
            <p className="text-sm text-[var(--dsp-text-muted)]">
              Modules: {modules.length ? modules.join(", ") : "Data unavailable."}
            </p>
            <label className="block text-sm">
              Module id
              <Input
                value={moduleId}
                onChange={(e) => setModuleId(e.target.value)}
                className="mt-1 max-w-sm"
              />
            </label>
            <label className="block text-sm">
              Reason
              <Input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="mt-1 max-w-lg"
              />
            </label>
            <label className="block text-sm">
              JSON patch
              <textarea
                className="mt-1 w-full max-w-2xl rounded-md border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-2 font-mono text-xs"
                rows={8}
                value={jsonPatch}
                onChange={(e) => setJsonPatch(e.target.value)}
              />
            </label>
            <Button type="button" onClick={() => updateMut.mutate()}>
              Save configuration
            </Button>
            <Suspense fallback={<p>Loading registry…</p>}>
              <LazyJsonPanel
                title="Full registry"
                data={registryQuery.data?.result}
                loading={registryQuery.isLoading}
                error={registryQuery.error ? "Data unavailable." : null}
              />
            </Suspense>
          </div>
        ) : null}

        {tab === "branding" ? (
          <div className="space-y-3">
            <p className="text-sm text-[var(--dsp-text-muted)]">
              Logo, theme, fonts, colors, login/landing/footer — config only.
            </p>
            <textarea
              className="w-full max-w-2xl rounded-md border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-2 font-mono text-xs"
              rows={8}
              value={jsonPatch}
              onChange={(e) => setJsonPatch(e.target.value)}
            />
            <Button type="button" onClick={() => brandingMut.mutate()}>
              Save branding
            </Button>
          </div>
        ) : null}

        {tab === "flags" ? (
          <div className="space-y-3">
            <label className="block text-sm">
              Flag key
              <Input
                value={flagKey}
                onChange={(e) => setFlagKey(e.target.value)}
                className="mt-1 max-w-sm"
              />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={flagEnabled}
                onChange={(e) => setFlagEnabled(e.target.checked)}
              />
              Enabled
            </label>
            <Button type="button" onClick={() => flagsMut.mutate()}>
              Update feature flag
            </Button>
          </div>
        ) : null}

        {tab === "ai" ? (
          <div className="space-y-3">
            <p className="text-sm text-[var(--dsp-text-muted)]">
              AI provider/model/temperature overlays — secrets never stored here.
            </p>
            <textarea
              className="w-full max-w-2xl rounded-md border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-2 font-mono text-xs"
              rows={8}
              value={jsonPatch}
              onChange={(e) => setJsonPatch(e.target.value)}
            />
            <Button type="button" onClick={() => aiMut.mutate()}>
              Save AI config
            </Button>
          </div>
        ) : null}

        {tab === "valuation" ? (
          <div className="space-y-3">
            <p className="text-sm text-[var(--dsp-text-muted)]">
              Valuation / MoS / sector default overlays only — engines are not run.
            </p>
            <textarea
              className="w-full max-w-2xl rounded-md border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-2 font-mono text-xs"
              rows={8}
              value={jsonPatch}
              onChange={(e) => setJsonPatch(e.target.value)}
            />
            <Button type="button" onClick={() => valuationMut.mutate()}>
              Save valuation overlay
            </Button>
          </div>
        ) : null}

        {tab === "rules" ? (
          <div className="space-y-3">
            <label className="block text-sm">
              Rule name
              <Input
                value={ruleName}
                onChange={(e) => setRuleName(e.target.value)}
                className="mt-1 max-w-sm"
              />
            </label>
            <Button type="button" onClick={() => ruleMut.mutate()}>
              Upsert business rule
            </Button>
            <Suspense fallback={<p>Loading rules…</p>}>
              <LazyJsonPanel
                title="Business rules"
                data={rulesQuery.data?.result}
                loading={rulesQuery.isLoading}
                error={rulesQuery.error ? "Data unavailable." : null}
              />
            </Suspense>
          </div>
        ) : null}

        {tab === "security" ? (
          <div className="space-y-3">
            <p className="text-sm text-[var(--dsp-text-muted)]">
              Password policy, MFA, session timeout, rate limits — overlays only.
            </p>
            <textarea
              className="w-full max-w-2xl rounded-md border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-2 font-mono text-xs"
              rows={8}
              value={jsonPatch}
              onChange={(e) => setJsonPatch(e.target.value)}
            />
            <Button type="button" onClick={() => securityMut.mutate()}>
              Save security config
            </Button>
          </div>
        ) : null}

        {tab === "history" ? (
          <div className="space-y-3">
            <label className="block text-sm">
              Rollback to version
              <Input
                value={rollbackVersion}
                onChange={(e) => setRollbackVersion(e.target.value)}
                className="mt-1 max-w-xs"
                inputMode="numeric"
              />
            </label>
            <Button type="button" onClick={() => rollbackMut.mutate()}>
              One-click rollback
            </Button>
            <Suspense fallback={<p>Loading history…</p>}>
              <LazyJsonPanel
                title="Configuration history"
                data={historyQuery.data?.result}
                loading={historyQuery.isLoading}
                error={historyQuery.error ? "Data unavailable." : null}
              />
            </Suspense>
          </div>
        ) : null}

        {tab === "monitoring" ? (
          <Suspense fallback={<p>Loading monitoring…</p>}>
            <LazyJsonPanel
              title="Monitoring Center (reuses Ops + Admin metrics)"
              data={monitoringQuery.data?.result}
              loading={monitoringQuery.isLoading}
              error={monitoringQuery.error ? "Data unavailable." : null}
            />
          </Suspense>
        ) : null}

        {tab === "audit" ? (
          <Suspense fallback={<p>Loading audit…</p>}>
            <LazyJsonPanel
              title="Configuration audit export"
              data={auditQuery.data?.result ?? historyQuery.data?.result}
              loading={auditQuery.isLoading}
              error={auditQuery.error ? "Data unavailable." : null}
            />
          </Suspense>
        ) : null}
      </div>
    </div>
  );
}

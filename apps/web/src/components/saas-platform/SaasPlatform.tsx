"use client";

/**
 * RC1 Milestone 9 — Commercial SaaS Platform shell.
 * Thin /api/v1/saas client — reuses enterprise domain; no fake payments.
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

const LazyAdminDashboard = lazy(() =>
  import("./SaasAdminDashboard").then((m) => ({
    default: m.SaasAdminDashboard,
  })),
);

const LazyPlanMatrix = lazy(() =>
  import("./SaasPlanMatrix").then((m) => ({ default: m.SaasPlanMatrix })),
);

type Tab =
  | "dashboard"
  | "organizations"
  | "plans"
  | "subscription"
  | "billing"
  | "license"
  | "usage"
  | "settings";

export function SaasPlatform() {
  const { session, user } = useAuth();
  const token = session?.accessToken;
  const actorId =
    (user as { id?: string } | null)?.id ||
    (user as { email?: string } | null)?.email ||
    "saas-admin";
  const opts = useMemo(() => ({ token }), [token]);
  const qc = useQueryClient();

  const [tab, setTab] = useState<Tab>("dashboard");
  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const [planId, setPlanId] = useState("professional");
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [timezone, setTimezone] = useState("UTC");
  const [currency, setCurrency] = useState("USD");
  const [taxId, setTaxId] = useState("");

  const dashQuery = useQuery({
    queryKey: ["saas-dashboard"],
    queryFn: () => api.saasDashboard(opts),
    enabled: featureFlags.saasPlatform,
    retry: false,
  });

  const orgsQuery = useQuery({
    queryKey: ["saas-orgs"],
    queryFn: () => api.saasListOrganizations(opts),
    enabled: featureFlags.saasPlatform,
    retry: false,
  });

  const plansQuery = useQuery({
    queryKey: ["saas-plans"],
    queryFn: () => api.saasPlans(opts),
    enabled: featureFlags.saasPlatform && tab === "plans",
    retry: false,
  });

  const subQuery = useQuery({
    queryKey: ["saas-sub", selectedOrgId],
    queryFn: () => api.saasGetSubscription(selectedOrgId!, opts),
    enabled: Boolean(selectedOrgId) && tab === "subscription",
    retry: false,
  });

  const billingQuery = useQuery({
    queryKey: ["saas-billing", selectedOrgId],
    queryFn: () => api.saasBillingStatus(selectedOrgId!, opts),
    enabled: Boolean(selectedOrgId) && tab === "billing",
    retry: false,
  });

  const licenseQuery = useQuery({
    queryKey: ["saas-license", selectedOrgId],
    queryFn: () => api.saasGetLicense(selectedOrgId!, opts),
    enabled: Boolean(selectedOrgId) && tab === "license",
    retry: false,
  });

  const usageQuery = useQuery({
    queryKey: ["saas-usage", selectedOrgId],
    queryFn: () => api.saasGetUsage(selectedOrgId!, opts),
    enabled: Boolean(selectedOrgId) && tab === "usage",
    retry: false,
  });

  const limitsQuery = useQuery({
    queryKey: ["saas-limits", selectedOrgId],
    queryFn: () => api.saasFeatureLimits(selectedOrgId!, opts),
    enabled: Boolean(selectedOrgId) && tab === "settings",
    retry: false,
  });

  const orgs = (orgsQuery.data?.result?.organizations || []) as Array<{
    org_id: string;
    name?: string;
    slug?: string;
    status?: string;
  }>;

  const createOrg = useMutation({
    mutationFn: () =>
      api.saasCreateOrganization(
        {
          name: orgName,
          slug: orgSlug,
          owner_user_id: actorId,
          actor_user_id: actorId,
          plan_id: planId,
        },
        opts,
      ),
    onSuccess: (res) => {
      const org = res.result?.organization as { org_id?: string } | undefined;
      setStatusMsg("Organization created.");
      setOrgName("");
      setOrgSlug("");
      if (org?.org_id) setSelectedOrgId(org.org_id);
      void qc.invalidateQueries({ queryKey: ["saas-orgs"] });
      void qc.invalidateQueries({ queryKey: ["saas-dashboard"] });
    },
    onError: (err) =>
      setStatusMsg((err as Error).message || "Data unavailable."),
  });

  const subscribe = useMutation({
    mutationFn: () => {
      if (!selectedOrgId) throw new Error("Select an organization");
      return api.saasCreateSubscription(
        {
          org_id: selectedOrgId,
          plan_id: planId,
          actor_user_id: actorId,
        },
        opts,
      );
    },
    onSuccess: () => {
      setStatusMsg("Subscription recorded (no payment executed).");
      void qc.invalidateQueries({ queryKey: ["saas-sub", selectedOrgId] });
      void qc.invalidateQueries({ queryKey: ["saas-dashboard"] });
    },
  });

  const checkout = useMutation({
    mutationFn: () => {
      if (!selectedOrgId) throw new Error("Select an organization");
      return api.saasCheckout(
        { org_id: selectedOrgId, plan_id: planId },
        opts,
      );
    },
    onSuccess: (res) => {
      const msg =
        (res.result?.message as string | undefined) ||
        res.message ||
        "Billing provider unavailable.";
      setStatusMsg(msg);
    },
  });

  const saveSettings = useMutation({
    mutationFn: () => {
      if (!selectedOrgId) throw new Error("Select an organization");
      return api.saasUpdateSettings(
        selectedOrgId,
        {
          actor_user_id: actorId,
          timezone,
          currency,
        },
        opts,
      );
    },
    onSuccess: () => setStatusMsg("Settings saved."),
  });

  const saveBillingProfile = useMutation({
    mutationFn: () => {
      if (!selectedOrgId) throw new Error("Select an organization");
      return api.saasUpsertBillingProfile(
        selectedOrgId,
        { tax_id: taxId, currency, tax_regime: "GST/VAT" },
        opts,
      );
    },
    onSuccess: () => setStatusMsg("Billing profile saved (metadata only)."),
  });

  const archiveOrg = useMutation({
    mutationFn: () => {
      if (!selectedOrgId) throw new Error("Select an organization");
      return api.saasArchiveOrganization(
        selectedOrgId,
        { actor_user_id: actorId },
        opts,
      );
    },
    onSuccess: () => {
      setStatusMsg("Organization archived.");
      void qc.invalidateQueries({ queryKey: ["saas-orgs"] });
    },
  });

  const trustSummary = useMemo(
    () =>
      dashboardSurfaceTrust({
        widgetCount: orgs.length,
        note: "Commercial SaaS Platform · enterprise reuse · no fake revenue",
      }),
    [orgs.length],
  );

  if (!featureFlags.saasPlatform) {
    return (
      <div className="space-y-4 p-6">
        <Alert variant="warning" title="SaaS platform disabled.">
          Set NEXT_PUBLIC_SAAS_PLATFORM=true to enable.
        </Alert>
      </div>
    );
  }

  const tabs: Tab[] = [
    "dashboard",
    "organizations",
    "plans",
    "subscription",
    "billing",
    "license",
    "usage",
    "settings",
  ];

  return (
    <div className="space-y-4 p-4 md:p-6" data-testid="saas-platform">
      <SurfaceTrustChrome summary={trustSummary} />
      <PageHeader
        title="Commercial SaaS Platform"
        description="Multi-tenant organizations, plans, licensing, and usage — thin client over /api/v1/saas. Reuses Enterprise IAM. No fabricated payments."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/portal">
              <Button size="sm" variant="secondary">
                Customer Portal
              </Button>
            </Link>
            <Link href="/ops">
              <Button size="sm" variant="secondary">
                Operations
              </Button>
            </Link>
          </div>
        }
      />

      {statusMsg ? (
        <p className="text-xs text-[var(--muted)]" role="status">
          {statusMsg}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-1">
        {tabs.map((t) => (
          <Button
            key={t}
            size="sm"
            variant={tab === t ? "primary" : "secondary"}
            onClick={() => setTab(t)}
          >
            {t}
          </Button>
        ))}
      </div>

      {selectedOrgId ? (
        <p className="text-xs text-[var(--muted)]">
          Selected org: <span className="font-mono">{selectedOrgId}</span>
        </p>
      ) : null}

      {tab === "dashboard" ? (
        <Suspense
          fallback={
            <p className="text-xs text-[var(--muted)]">Loading dashboard…</p>
          }
        >
          <LazyAdminDashboard
            data={dashQuery.data?.result}
            loading={dashQuery.isLoading}
            error={dashQuery.isError}
          />
        </Suspense>
      ) : null}

      {tab === "organizations" ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <section className="space-y-2 rounded-md border border-[var(--border)] p-3">
            <h2 className="text-sm font-medium">Create organization</h2>
            <Input
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              placeholder="Name"
              aria-label="Organization name"
            />
            <Input
              value={orgSlug}
              onChange={(e) => setOrgSlug(e.target.value)}
              placeholder="slug-example"
              aria-label="Organization slug"
            />
            <select
              className="w-full rounded border border-[var(--border)] bg-transparent px-2 py-1 text-sm"
              value={planId}
              onChange={(e) => setPlanId(e.target.value)}
              aria-label="Initial plan"
            >
              <option value="starter">Starter</option>
              <option value="professional">Professional</option>
              <option value="enterprise">Enterprise</option>
              <option value="custom">Custom</option>
            </select>
            <Button
              size="sm"
              disabled={!orgName.trim() || !orgSlug.trim() || createOrg.isPending}
              onClick={() => createOrg.mutate()}
            >
              Create
            </Button>
          </section>
          <section className="space-y-2 rounded-md border border-[var(--border)] p-3">
            <h2 className="text-sm font-medium">Organizations</h2>
            <ul className="max-h-80 space-y-1 overflow-auto text-sm">
              {orgs.map((o) => (
                <li key={o.org_id}>
                  <button
                    type="button"
                    className="w-full rounded px-2 py-1 text-left hover:bg-[var(--surface-2)]"
                    onClick={() => setSelectedOrgId(o.org_id)}
                  >
                    <span className="font-medium">{o.name}</span>
                    <span className="ml-2 text-[10px] text-[var(--muted)]">
                      {o.slug} · {o.status}
                    </span>
                  </button>
                </li>
              ))}
              {orgs.length === 0 ? (
                <li className="text-xs text-[var(--muted)]">
                  No organizations available.
                </li>
              ) : null}
            </ul>
            {selectedOrgId ? (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => archiveOrg.mutate()}
              >
                Archive selected
              </Button>
            ) : null}
          </section>
        </div>
      ) : null}

      {tab === "plans" ? (
        <Suspense
          fallback={
            <p className="text-xs text-[var(--muted)]">Loading plans…</p>
          }
        >
          <LazyPlanMatrix data={plansQuery.data?.result} />
        </Suspense>
      ) : null}

      {tab === "subscription" ? (
        <section className="space-y-3 rounded-md border border-[var(--border)] p-3">
          {!selectedOrgId ? (
            <p className="text-sm text-[var(--muted)]">
              Select an organization first.
            </p>
          ) : (
            <>
              <select
                className="rounded border border-[var(--border)] bg-transparent px-2 py-1 text-sm"
                value={planId}
                onChange={(e) => setPlanId(e.target.value)}
                aria-label="Plan"
              >
                <option value="starter">Starter</option>
                <option value="professional">Professional</option>
                <option value="enterprise">Enterprise</option>
                <option value="custom">Custom</option>
              </select>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" onClick={() => subscribe.mutate()}>
                  Assign subscription
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => checkout.mutate()}
                >
                  Checkout
                </Button>
              </div>
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded border border-[var(--border)] p-2 text-xs">
                {JSON.stringify(subQuery.data?.result || {}, null, 2)}
              </pre>
            </>
          )}
        </section>
      ) : null}

      {tab === "billing" ? (
        <section className="space-y-3 rounded-md border border-[var(--border)] p-3">
          {!selectedOrgId ? (
            <p className="text-sm text-[var(--muted)]">
              Select an organization first.
            </p>
          ) : (
            <>
              <Alert variant="warning" title="Billing provider interfaces only.">
                Checkout and invoices stay unavailable until a payment gateway
                is configured. No fake charges.
              </Alert>
              <Input
                value={taxId}
                onChange={(e) => setTaxId(e.target.value)}
                placeholder="Tax ID / GSTIN / VAT"
                aria-label="Tax identifier"
              />
              <Button size="sm" onClick={() => saveBillingProfile.mutate()}>
                Save billing profile
              </Button>
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded border border-[var(--border)] p-2 text-xs">
                {JSON.stringify(billingQuery.data?.result || {}, null, 2)}
              </pre>
            </>
          )}
        </section>
      ) : null}

      {tab === "license" ? (
        <section className="rounded-md border border-[var(--border)] p-3">
          {!selectedOrgId ? (
            <p className="text-sm text-[var(--muted)]">
              Select an organization first.
            </p>
          ) : (
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap text-xs">
              {JSON.stringify(licenseQuery.data?.result || {}, null, 2)}
            </pre>
          )}
        </section>
      ) : null}

      {tab === "usage" ? (
        <section className="rounded-md border border-[var(--border)] p-3">
          {!selectedOrgId ? (
            <p className="text-sm text-[var(--muted)]">
              Select an organization first.
            </p>
          ) : (
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap text-xs">
              {JSON.stringify(usageQuery.data?.result || {}, null, 2)}
            </pre>
          )}
        </section>
      ) : null}

      {tab === "settings" ? (
        <section className="space-y-3 rounded-md border border-[var(--border)] p-3">
          {!selectedOrgId ? (
            <p className="text-sm text-[var(--muted)]">
              Select an organization first.
            </p>
          ) : (
            <>
              <Input
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                aria-label="Timezone"
                placeholder="Timezone"
              />
              <Input
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                aria-label="Currency"
                placeholder="Currency"
              />
              <Button size="sm" onClick={() => saveSettings.mutate()}>
                Save settings
              </Button>
              <h3 className="text-xs font-medium uppercase text-[var(--muted)]">
                Feature limits (plan)
              </h3>
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap text-xs">
                {JSON.stringify(limitsQuery.data?.result || {}, null, 2)}
              </pre>
            </>
          )}
        </section>
      ) : null}
    </div>
  );
}

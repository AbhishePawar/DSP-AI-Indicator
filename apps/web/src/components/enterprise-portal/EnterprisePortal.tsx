"use client";

/**
 * EPS-002 — Customer Portal (thin client).
 * Displays org / license / members / usage / invoices / API keys / settings
 * from /api/v1/enterprise. Never fabricates commercial data.
 */

import { useEffect, useState } from "react";

import {
  fetchCustomerPortal,
  listOrganizations,
} from "@/lib/enterprise/enterpriseClient";
import type { CustomerPortal, Organization } from "@/lib/enterprise/types";
import { useAuth } from "@/lib/auth/AuthProvider";

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-sm text-[var(--muted)]" role="status">
      {children}
    </p>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section
      className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4"
      aria-labelledby={`panel-${title.replace(/\s+/g, "-").toLowerCase()}`}
    >
      <h2
        id={`panel-${title.replace(/\s+/g, "-").toLowerCase()}`}
        className="mb-3 text-base font-semibold text-[var(--fg)]"
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

export function EnterprisePortal() {
  const { user } = useAuth();
  const userId = user?.subject || null;
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [orgMessage, setOrgMessage] = useState<string | null>(null);
  const [selectedOrgId, setSelectedOrgId] = useState<string>("");
  const [portal, setPortal] = useState<CustomerPortal | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const listed = await listOrganizations(userId ?? undefined);
        if (cancelled) return;
        setOrgs(listed.result);
        setOrgMessage(listed.message);
        if (listed.result.length > 0) {
          setSelectedOrgId((prev) => prev || listed.result[0].org_id);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Data unavailable.");
          setOrgMessage("No organizations available.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [userId]);

  useEffect(() => {
    if (!selectedOrgId || !userId) {
      setPortal(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchCustomerPortal(selectedOrgId, userId);
        if (!cancelled) setPortal(data);
      } catch (err) {
        if (!cancelled) {
          setPortal(null);
          setError(err instanceof Error ? err.message : "Data unavailable.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedOrgId, userId]);

  if (loading) {
    return <Empty>Loading customer portal…</Empty>;
  }

  return (
    <div className="space-y-4" data-testid="enterprise-portal">
      {error ? (
        <p className="text-sm text-[var(--danger-fg)]" role="alert">
          {error}
        </p>
      ) : null}

      <Panel title="Organization">
        {orgs.length === 0 ? (
          <Empty>{orgMessage || "No organizations available."}</Empty>
        ) : (
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <label className="text-sm text-[var(--muted)]" htmlFor="org-select">
              Active organization
            </label>
            <select
              id="org-select"
              className="rounded border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm"
              value={selectedOrgId}
              onChange={(e) => setSelectedOrgId(e.target.value)}
            >
              {orgs.map((o) => (
                <option key={o.org_id} value={o.org_id}>
                  {o.name} ({o.slug})
                </option>
              ))}
            </select>
          </div>
        )}
        {portal ? (
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-[var(--muted)]">Status</dt>
              <dd>{portal.organization.status}</dd>
            </div>
            <div>
              <dt className="text-[var(--muted)]">Seat limit</dt>
              <dd>{portal.organization.seat_limit ?? "Data unavailable."}</dd>
            </div>
          </dl>
        ) : null}
      </Panel>

      <Panel title="License">
        {!portal ? (
          <Empty>No license assigned.</Empty>
        ) : !portal.license.available ? (
          <Empty>{portal.license.message || "No license assigned."}</Empty>
        ) : (
          <dl className="grid gap-2 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-[var(--muted)]">Tier</dt>
              <dd>{portal.license.license?.tier}</dd>
            </div>
            <div>
              <dt className="text-[var(--muted)]">Seats</dt>
              <dd>{portal.license.license?.seats}</dd>
            </div>
            <div>
              <dt className="text-[var(--muted)]">Status</dt>
              <dd>{portal.license.license?.status}</dd>
            </div>
          </dl>
        )}
      </Panel>

      <Panel title="Members">
        {!portal || portal.members.length === 0 ? (
          <Empty>{portal?.members_message || "No members available."}</Empty>
        ) : (
          <ul className="divide-y divide-[var(--border)] text-sm">
            {portal.members.map((m) => (
              <li key={m.user_id} className="flex justify-between py-2">
                <span>{m.user_id}</span>
                <span className="text-[var(--muted)]">{m.role_id}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title="Usage">
        {!portal?.usage?.available ? (
          <Empty>Usage analytics unavailable.</Empty>
        ) : (
          <dl className="grid gap-2 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-[var(--muted)]">DAU</dt>
              <dd>{portal.usage.dau ?? 0}</dd>
            </div>
            <div>
              <dt className="text-[var(--muted)]">Research</dt>
              <dd>{portal.usage.research_count ?? 0}</dd>
            </div>
            <div>
              <dt className="text-[var(--muted)]">Exports</dt>
              <dd>{portal.usage.export_count ?? 0}</dd>
            </div>
            <div>
              <dt className="text-[var(--muted)]">Comparisons</dt>
              <dd>{portal.usage.comparison_count ?? 0}</dd>
            </div>
            <div>
              <dt className="text-[var(--muted)]">API requests</dt>
              <dd>{portal.usage.api_request_count ?? 0}</dd>
            </div>
            <div>
              <dt className="text-[var(--muted)]">Storage (bytes)</dt>
              <dd>{portal.usage.storage_bytes ?? 0}</dd>
            </div>
          </dl>
        )}
      </Panel>

      <Panel title="Billing & Invoices">
        <Empty>
          {portal?.billing?.message || "Billing unavailable."}
        </Empty>
        <p className="mt-2 text-xs text-[var(--muted)]">
          No checkout or payment simulation. Provider adapters only.
        </p>
      </Panel>

      <Panel title="API Keys">
        {!portal || portal.api_keys.keys.length === 0 ? (
          <Empty>{portal?.api_keys.message || "No API keys."}</Empty>
        ) : (
          <ul className="divide-y divide-[var(--border)] text-sm">
            {portal.api_keys.keys.map((k) => (
              <li key={k.key_id} className="flex justify-between py-2">
                <span>{k.name}</span>
                <span className="text-[var(--muted)]">{k.status}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title="Settings">
        {!portal ? (
          <Empty>Data unavailable.</Empty>
        ) : (
          <p className="text-sm text-[var(--muted)]">
            Branding and preferences are managed server-side. Portal displays
            organization settings only — no secrets are exposed to the browser.
          </p>
        )}
      </Panel>
    </div>
  );
}

"use client";

/**
 * Figma `Advisor.tsx` — four stat cards · "Client Portfolios" table with
 * "+ Add Client" and per-row "View →".
 *
 * Data: `GET/POST/PUT/DELETE /api/v1/advisor/clients` (per-advisor book).
 * Portfolio value is advisor-entered; a missing value renders
 * "Data unavailable." A Portfolio Rating column is shown only as
 * "Not available." — no rating is derived in the browser (CV-001/CV-002).
 */

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { FigmaPage, Panel, PanelEmpty, StatCard, TH_CLASS, TD_CLASS } from "@/components/pages/PagePrimitives";
import { api } from "@/lib/api/client";
import type { AdvisorClient, AdvisorClientPayload, AdvisorRiskProfile } from "@/lib/api/workspaceTypes";
import { useAuth } from "@/lib/auth/AuthProvider";

const QUERY_KEY = ["advisor", "clients"] as const;
const INPUT =
  "w-full rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-[13px] text-[var(--fg)] placeholder:text-[var(--muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]";
const LABEL = "mb-1.5 block font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.06em] text-[var(--muted)]";

const RISK_LABEL: Record<AdvisorRiskProfile, string> = {
  conservative: "Conservative",
  moderate: "Moderate",
  aggressive: "Aggressive",
};
const RISK_COLOR: Record<AdvisorRiskProfile, string> = {
  conservative: "var(--c-profit)",
  moderate: "var(--c-revenue)",
  aggressive: "var(--c-risk)",
};

/** Indian-style compact currency for advisor-entered values (display only). */
export function formatInr(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Data unavailable.";
  const abs = Math.abs(value);
  if (abs >= 1e7) return `₹${(value / 1e7).toFixed(2).replace(/\.?0+$/, "")}Cr`;
  if (abs >= 1e5) return `₹${(value / 1e5).toFixed(2).replace(/\.?0+$/, "")}L`;
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

type FormState = { name: string; email: string; risk_profile: AdvisorRiskProfile; portfolio_value: string; notes: string };
const EMPTY_FORM: FormState = { name: "", email: "", risk_profile: "moderate", portfolio_value: "", notes: "" };

function toPayload(form: FormState): AdvisorClientPayload | string {
  const name = form.name.trim();
  if (!name) return "Client name is required.";
  const email = form.email.trim();
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return "Enter a valid email address.";
  let portfolio_value: number | null = null;
  if (form.portfolio_value.trim()) {
    const n = Number(form.portfolio_value.replace(/[,₹\s]/g, ""));
    if (!Number.isFinite(n) || n < 0) return "Portfolio value must be a non-negative number (₹).";
    portfolio_value = n;
  }
  return {
    name,
    risk_profile: form.risk_profile,
    email: email || null,
    portfolio_value,
    notes: form.notes.trim() || null,
  };
}

function ClientForm({
  initial,
  submitting,
  error,
  onCancel,
  onSubmit,
  heading,
}: {
  initial: FormState;
  submitting: boolean;
  error: string | null;
  onCancel: () => void;
  onSubmit: (payload: AdvisorClientPayload) => void;
  heading: string;
}) {
  const [form, setForm] = useState<FormState>(initial);
  const [localError, setLocalError] = useState<string | null>(null);

  function submit(e: FormEvent) {
    e.preventDefault();
    const payload = toPayload(form);
    if (typeof payload === "string") {
      setLocalError(payload);
      return;
    }
    setLocalError(null);
    onSubmit(payload);
  }

  const shownError = localError ?? error;
  return (
    <form onSubmit={submit} className="border-b border-[var(--border)] bg-[var(--surface)] px-5 py-4" aria-label={heading} noValidate>
      <p className="mb-3 text-[13px] font-medium text-[var(--fg)]">{heading}</p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label htmlFor="client-name" className={LABEL}>Client name *</label>
          <input id="client-name" className={INPUT} value={form.name} required maxLength={120} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div>
          <label htmlFor="client-email" className={LABEL}>Email</label>
          <input id="client-email" type="email" className={INPUT} value={form.email} maxLength={254} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div>
          <label htmlFor="client-risk" className={LABEL}>Risk profile *</label>
          <select id="client-risk" className={INPUT} value={form.risk_profile} onChange={(e) => setForm({ ...form, risk_profile: e.target.value as AdvisorRiskProfile })}>
            {(Object.keys(RISK_LABEL) as AdvisorRiskProfile[]).map((k) => (
              <option key={k} value={k}>{RISK_LABEL[k]}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="client-value" className={LABEL}>Portfolio value (₹)</label>
          <input id="client-value" inputMode="numeric" className={`${INPUT} font-[family-name:var(--font-mono)]`} value={form.portfolio_value} placeholder="Optional" onChange={(e) => setForm({ ...form, portfolio_value: e.target.value })} />
        </div>
        <div className="sm:col-span-2 lg:col-span-4">
          <label htmlFor="client-notes" className={LABEL}>Notes</label>
          <textarea id="client-notes" rows={2} className={INPUT} value={form.notes} maxLength={1000} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </div>
      </div>
      {shownError ? (
        <p role="alert" className="mt-3 text-xs text-[var(--danger-fg)]">{shownError}</p>
      ) : null}
      <div className="mt-3 flex gap-2">
        <button type="submit" disabled={submitting} className="min-h-9 rounded-lg bg-[var(--c-dsp)] px-4 text-xs font-medium text-white disabled:opacity-50">
          {submitting ? "Saving…" : "Save client"}
        </button>
        <button type="button" onClick={onCancel} disabled={submitting} className="min-h-9 rounded-lg border border-[var(--border)] px-4 text-xs text-[var(--muted)] hover:text-[var(--fg)]">
          Cancel
        </button>
      </div>
    </form>
  );
}

export function AdvisorClients() {
  const { session } = useAuth();
  const token = session?.accessToken;
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<{ kind: "idle" } | { kind: "create" } | { kind: "edit"; client: AdvisorClient }>({ kind: "idle" });

  const clientsQuery = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => api.advisorClients({ token }),
    enabled: Boolean(token),
    retry: false,
    staleTime: 15_000,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: QUERY_KEY });

  const createMutation = useMutation({
    mutationFn: (payload: AdvisorClientPayload) => api.advisorClientCreate(payload, { token }),
    onSuccess: async () => {
      setMode({ kind: "idle" });
      await invalidate();
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: AdvisorClientPayload }) => api.advisorClientUpdate(id, payload, { token }),
    onSuccess: async () => {
      setMode({ kind: "idle" });
      await invalidate();
    },
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.advisorClientDelete(id, { token }),
    onSuccess: invalidate,
  });
  const sessionMutation = useMutation({
    mutationFn: (id: string) => api.advisorClientRecordSession(id, { token }),
    onSuccess: invalidate,
  });

  const data = clientsQuery.data;
  const clients = data?.items ?? [];
  const overview = data?.overview;

  const aumNote =
    overview && overview.clients_with_portfolio_value < overview.active_clients
      ? `${overview.clients_with_portfolio_value} of ${overview.active_clients} clients have a recorded value`
      : undefined;

  return (
    <FigmaPage title="Advisor" subtitle="Client portfolio management · Research delegation">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Total Clients" value={overview ? String(overview.active_clients) : "Data unavailable."} />
        <StatCard
          label="AUM (recorded)"
          value={overview ? formatInr(overview.total_portfolio_value) : "Data unavailable."}
          tone="profit"
          note={aumNote}
        />
        <StatCard label="Avg Rating" value="Data unavailable." tone="muted" note="Client ratings require DSP research on each portfolio." />
        <StatCard label="Research Sessions" value={overview ? String(overview.research_sessions) : "Data unavailable."} note="Total logged for your clients" />
      </div>

      <Panel
        title="Client Portfolios"
        action={
          <button
            type="button"
            onClick={() => setMode(mode.kind === "create" ? { kind: "idle" } : { kind: "create" })}
            disabled={!token}
            aria-expanded={mode.kind === "create"}
            className="min-h-8 rounded-lg bg-[var(--c-dsp)] px-3.5 text-xs font-medium text-white disabled:opacity-50"
          >
            + Add Client
          </button>
        }
      >
        {mode.kind === "create" ? (
          <ClientForm
            heading="New client"
            initial={EMPTY_FORM}
            submitting={createMutation.isPending}
            error={createMutation.error instanceof Error ? createMutation.error.message : null}
            onCancel={() => setMode({ kind: "idle" })}
            onSubmit={(payload) => createMutation.mutate(payload)}
          />
        ) : null}
        {mode.kind === "edit" ? (
          <ClientForm
            key={mode.client.client_id}
            heading={`Edit ${mode.client.name}`}
            initial={{
              name: mode.client.name,
              email: mode.client.email ?? "",
              risk_profile: mode.client.risk_profile,
              portfolio_value: mode.client.portfolio_value === null ? "" : String(mode.client.portfolio_value),
              notes: mode.client.notes ?? "",
            }}
            submitting={updateMutation.isPending}
            error={updateMutation.error instanceof Error ? updateMutation.error.message : null}
            onCancel={() => setMode({ kind: "idle" })}
            onSubmit={(payload) => updateMutation.mutate({ id: mode.client.client_id, payload })}
          />
        ) : null}

        {!token ? (
          <PanelEmpty title="Sign in required." description="Your client book is private to your advisor account." />
        ) : clientsQuery.isPending ? (
          <PanelEmpty title="Loading clients…" />
        ) : clientsQuery.isError ? (
          <PanelEmpty
            title="Clients unavailable."
            description={clientsQuery.error instanceof Error ? clientsQuery.error.message : "The advisor service did not respond."}
            action={
              <button type="button" onClick={() => clientsQuery.refetch()} className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs text-[var(--fg)]">
                Retry
              </button>
            }
          />
        ) : clients.length === 0 ? (
          <PanelEmpty title="No clients yet." description="Use “+ Add Client” to register your first client. Nothing is prefilled." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  {["Client", "Portfolio Value", "Risk Profile", "Portfolio Rating", "Research Sessions", ""].map((h, i) => (
                    <th key={h || `col-${i}`} scope="col" className={TH_CLASS}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {clients.map((c, i) => (
                  <tr key={c.client_id} className={i < clients.length - 1 ? "border-b border-[var(--border)]" : ""}>
                    <td className={TD_CLASS}>
                      <div className="flex items-center gap-2.5">
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface-2)] text-[13px] font-semibold text-[var(--fg)]" aria-hidden="true">
                          {c.name[0]?.toUpperCase()}
                        </span>
                        <div className="min-w-0">
                          <p className="truncate">{c.name}</p>
                          {c.email ? <p className="truncate text-[11px] text-[var(--muted)]">{c.email}</p> : null}
                        </div>
                      </div>
                    </td>
                    <td className={`${TD_CLASS} font-[family-name:var(--font-mono)] ${c.portfolio_value === null ? "text-[var(--muted)]" : ""}`}>
                      {formatInr(c.portfolio_value)}
                    </td>
                    <td className={TD_CLASS}>
                      <span className="rounded-md bg-[var(--surface-2)] px-2 py-0.5 font-[family-name:var(--font-mono)] text-xs" style={{ color: RISK_COLOR[c.risk_profile] }}>
                        {RISK_LABEL[c.risk_profile]}
                      </span>
                    </td>
                    <td className={`${TD_CLASS} text-xs text-[var(--muted)]`}>Not available.</td>
                    <td className={`${TD_CLASS} font-[family-name:var(--font-mono)] text-[var(--muted)]`}>{c.research_sessions}</td>
                    <td className={`${TD_CLASS} whitespace-nowrap`}>
                      <div className="flex justify-end gap-1.5">
                        <Link
                          href="/analysis"
                          onClick={() => sessionMutation.mutate(c.client_id)}
                          className="rounded-md border border-[color-mix(in_srgb,var(--c-dsp)_20%,transparent)] bg-[color-mix(in_srgb,var(--c-dsp)_10%,transparent)] px-2.5 py-1 text-[11px] text-[var(--c-dsp)]"
                          aria-label={`Start research session for ${c.name}`}
                        >
                          View →
                        </Link>
                        <button type="button" onClick={() => setMode({ kind: "edit", client: c })} className="rounded-md border border-[var(--border)] px-2.5 py-1 text-[11px] text-[var(--muted)] hover:text-[var(--fg)]" aria-label={`Edit ${c.name}`}>
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            if (window.confirm(`Remove ${c.name} from your client book?`)) deleteMutation.mutate(c.client_id);
                          }}
                          disabled={deleteMutation.isPending}
                          className="rounded-md border border-[var(--border)] px-2.5 py-1 text-[11px] text-[var(--muted)] hover:text-[var(--c-risk)]"
                          aria-label={`Remove ${c.name}`}
                        >
                          Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </FigmaPage>
  );
}

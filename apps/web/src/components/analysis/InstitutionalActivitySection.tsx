"use client";

/**
 * InstitutionalActivitySection — compact research-terminal block.
 *
 * Data sources (existing only — no mock data, no new endpoints):
 *   - api.ownership(symbol)  → GET /api/v1/ownership
 *       • stakes[]           → holder_name, holder_type, percent_held, shares_held
 *       • promoter_holding_percent, institutional_holding_percent, public_holding_percent
 *       • as_of              → data date
 *       • available / authenticated → gate display
 *
 * Rendering rules:
 *   - Available fields: show with colour-coded accent
 *   - Unavailable / null fields: show "—" in muted colour (never invent)
 *   - Unauthenticated: show auth-required notice
 *   - Not yet loaded: show "Load" prompt
 *   - Terminal aesthetic: monospace values, compact rows, dense grid
 */

import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { OwnershipPayload } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

/* ─── Helpers ────────────────────────────────────────────────────── */

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${v.toFixed(2)}%`;
}

function fmtShares(v: number | null | undefined): string {
  if (v == null) return "—";
  if (v >= 1_00_00_000) return `${(v / 1_00_00_000).toFixed(2)} Cr`;
  if (v >= 1_00_000) return `${(v / 1_00_000).toFixed(2)} L`;
  return v.toLocaleString("en-IN");
}

function holderTypeLabel(t: string | undefined): string {
  if (!t) return "—";
  if (t === "mutual_fund") return "Mutual Fund";
  if (t === "institutional") return "Institution";
  if (t === "promoter") return "Promoter";
  if (t === "public") return "Public";
  return t.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function holderTypeTone(t: string | undefined): "accent" | "success" | "warning" | "neutral" {
  if (t === "mutual_fund") return "accent";
  if (t === "institutional") return "success";
  if (t === "promoter") return "warning";
  return "neutral";
}

function pctColour(v: number | null | undefined): string {
  if (v == null) return "text-[var(--muted)]";
  if (v >= 50) return "text-emerald-400";
  if (v >= 20) return "text-amber-400";
  return "text-[var(--fg)]";
}

function describeError(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401 || error.status === 403)
      return "Authentication required. Please sign in to view institutional holdings.";
    return error.message || `API error (${error.status})`;
  }
  if (error instanceof Error) return error.message;
  return "Data unavailable.";
}

/* ─── Aggregate holding bar ──────────────────────────────────────── */

interface HoldingBarProps {
  promoter: number | null | undefined;
  institutional: number | null | undefined;
  publicHolding: number | null | undefined;
}

function HoldingBar({ promoter, institutional, publicHolding }: HoldingBarProps) {
  const hasAny = promoter != null || institutional != null || publicHolding != null;
  if (!hasAny) return null;

  const p = promoter ?? 0;
  const i = institutional ?? 0;
  const pub = publicHolding ?? 0;
  const total = p + i + pub;
  const scale = total > 0 ? 100 / total : 1;

  return (
    <div className="space-y-2">
      <div className="flex h-2 w-full overflow-hidden rounded-full bg-[var(--surface-2)]">
        {p > 0 && (
          <div
            className="h-full bg-amber-400"
            style={{ width: `${p * scale}%` }}
            title={`Promoter: ${fmtPct(p)}`}
          />
        )}
        {i > 0 && (
          <div
            className="h-full bg-emerald-400"
            style={{ width: `${i * scale}%` }}
            title={`Institutional: ${fmtPct(i)}`}
          />
        )}
        {pub > 0 && (
          <div
            className="h-full bg-[var(--accent)]"
            style={{ width: `${pub * scale}%` }}
            title={`Public: ${fmtPct(pub)}`}
          />
        )}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-sm bg-amber-400" />
          <span className="text-[var(--muted)]">Promoter</span>
          <span className={["font-mono font-semibold", pctColour(promoter)].join(" ")}>
            {fmtPct(promoter)}
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-sm bg-emerald-400" />
          <span className="text-[var(--muted)]">Institutional</span>
          <span className={["font-mono font-semibold", pctColour(institutional)].join(" ")}>
            {fmtPct(institutional)}
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-sm bg-[var(--accent)]" />
          <span className="text-[var(--muted)]">Public</span>
          <span className={["font-mono font-semibold", pctColour(publicHolding)].join(" ")}>
            {fmtPct(publicHolding)}
          </span>
        </span>
      </div>
    </div>
  );
}

/* ─── Stakes table ───────────────────────────────────────────────── */

type Stake = NonNullable<OwnershipPayload["stakes"]>[number];

function StakesTable({ stakes }: { stakes: Stake[] }) {
  if (stakes.length === 0) {
    return (
      <p className="py-4 text-center text-xs text-[var(--muted)]">
        No individual institutional or mutual fund stakes available in this data set.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto -mx-0">
      <table className="w-full min-w-[400px] text-xs">
        <thead>
          <tr className="border-b border-[var(--border)] text-left">
            <th className="pb-2 pr-3 font-medium text-[var(--muted)]">Holder</th>
            <th className="pb-2 pr-3 font-medium text-[var(--muted)]">Type</th>
            <th className="pb-2 pr-3 text-right font-medium text-[var(--muted)]">% Held</th>
            <th className="pb-2 text-right font-medium text-[var(--muted)]">Shares</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border)]">
          {stakes.map((s, i) => (
            <tr key={i} className="group hover:bg-[var(--surface-2)]">
              <td className="py-2 pr-3 font-medium text-[var(--fg)] max-w-[140px] break-words">
                {s.holder_name ?? "—"}
              </td>
              <td className="py-2 pr-3">
                <Badge tone={holderTypeTone(s.holder_type)} className="text-[10px] px-1.5 py-0.5 whitespace-nowrap">
                  {holderTypeLabel(s.holder_type)}
                </Badge>
              </td>
              <td className={["py-2 pr-3 text-right font-mono font-semibold whitespace-nowrap", pctColour(s.percent_held)].join(" ")}>
                {fmtPct(s.percent_held)}
              </td>
              <td className="py-2 text-right font-mono text-[var(--muted)] whitespace-nowrap">
                {fmtShares(s.shares_held)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ─── Main component ─────────────────────────────────────────────── */

interface InstitutionalActivitySectionProps {
  symbol: string;
}

export function InstitutionalActivitySection({ symbol }: InstitutionalActivitySectionProps) {
  const { session } = useAuth();
  const token = session?.accessToken ?? null;

  const mutation = useMutation({
    mutationFn: () => api.ownership(symbol, { token }),
  });

  const data = mutation.data as OwnershipPayload | undefined;

  /* Filter to institutional + MF stakes only for the detail table */
  const instMfStakes: Stake[] = (data?.stakes ?? []).filter(
    (s) => s.holder_type === "institutional" || s.holder_type === "mutual_fund",
  );

  /* All stakes for the full breakdown (if available) */
  const allStakes: Stake[] = data?.stakes ?? [];

  const asOf = data?.as_of
    ? new Date(data.as_of).toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      })
    : null;

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* ── Header row ─────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-[var(--muted)] uppercase tracking-widest text-[10px]">
            Institutional &amp; MF Activity
          </span>
          {asOf && (
            <span className="rounded bg-[var(--surface-2)] px-1.5 py-0.5 text-[10px] text-[var(--muted)]">
              as of {asOf}
            </span>
          )}
          {data?.available === false && (
            <Badge tone="neutral" className="text-[10px]">Data Unavailable</Badge>
          )}
        </div>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="text-xs"
        >
          {mutation.isPending ? "Loading…" : mutation.data ? "Refresh" : "Load Holdings"}
        </Button>
      </div>

      {/* ── Idle state ─────────────────────────────────────────── */}
      {!mutation.data && !mutation.isPending && !mutation.isError && (
        <div className="rounded border border-dashed border-[var(--border)] px-4 py-6 text-center">
          <p className="text-[var(--muted)]">
            Click <span className="text-[var(--fg)]">&ldquo;Load Holdings&rdquo;</span> to fetch
            institutional and mutual fund shareholding data from{" "}
            <span className="text-[var(--accent)]">/api/v1/ownership</span>.
          </p>
        </div>
      )}

      {/* ── Loading skeleton ────────────────────────────────────── */}
      {mutation.isPending && (
        <div className="space-y-2">
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-6 w-3/4" />
          <Skeleton className="h-6 w-5/6" />
        </div>
      )}

      {/* ── Error state ─────────────────────────────────────────── */}
      {mutation.isError && (
        <div className="rounded border border-[var(--danger-fg)]/30 bg-[var(--danger-fg)]/5 px-4 py-3">
          <p className="text-[var(--danger-fg)]">{describeError(mutation.error)}</p>
        </div>
      )}

      {/* ── Data available ──────────────────────────────────────── */}
      {mutation.data && !mutation.isPending && (
        <div className="space-y-5">
          {/* Availability notice */}
          {data?.available === false && (
            <div className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-[var(--muted)]">
              {data.message ?? "Ownership data is not available for this symbol from the configured providers."}
            </div>
          )}

          {/* Aggregate holding bar */}
          {(data?.promoter_holding_percent != null ||
            data?.institutional_holding_percent != null ||
            data?.public_holding_percent != null) && (
            <div className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 space-y-3">
              <p className="text-[10px] uppercase tracking-widest text-[var(--muted)]">
                Shareholding Pattern
              </p>
              <HoldingBar
                promoter={data?.promoter_holding_percent}
                institutional={data?.institutional_holding_percent}
                publicHolding={data?.public_holding_percent}
              />
            </div>
          )}

          {/* Institutional + MF detail table */}
          {data?.available !== false && (
            <div className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-[10px] uppercase tracking-widest text-[var(--muted)]">
                  Institutional &amp; Mutual Fund Stakes
                </p>
                {instMfStakes.length > 0 && (
                  <span className="rounded bg-[var(--accent)]/10 px-1.5 py-0.5 text-[10px] text-[var(--accent)]">
                    {instMfStakes.length} holder{instMfStakes.length !== 1 ? "s" : ""}
                  </span>
                )}
              </div>
              <StakesTable stakes={instMfStakes} />
            </div>
          )}

          {/* All stakes (if any non-inst/mf exist and available) */}
          {data?.available !== false && allStakes.length > instMfStakes.length && (
            <div className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 space-y-3">
              <p className="text-[10px] uppercase tracking-widest text-[var(--muted)]">
                All Reported Stakes
              </p>
              <StakesTable stakes={allStakes} />
            </div>
          )}

          {/* Data provenance */}
          {data?.provenance && (
            <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-[var(--border)] pt-2 text-[10px] text-[var(--muted)]">
              {data.provenance.provider_name && (
                <span>
                  Source:{" "}
                  <span className="text-[var(--fg)]">
                    {String(data.provenance.provider_name)}
                  </span>
                </span>
              )}
              {data.provenance.retrieved_at && (
                <span>
                  Retrieved:{" "}
                  <span className="text-[var(--fg)]">
                    {new Date(String(data.provenance.retrieved_at)).toLocaleDateString("en-IN", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })}
                  </span>
                </span>
              )}
              {data.provenance.cache_hit != null && (
                <span>
                  Cache:{" "}
                  <span className="text-[var(--fg)]">
                    {data.provenance.cache_hit ? "Hit" : "Miss"}
                  </span>
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

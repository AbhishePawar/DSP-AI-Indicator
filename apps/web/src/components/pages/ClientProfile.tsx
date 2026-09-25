"use client";

/**
 * Figma `ClientProfile.tsx` — "Your Financial Profile" · completion bar ·
 * five form SectionCards (left) · sticky Financial Health Score card with
 * semicircular gauge, "What influences your score?" rows and insight (right).
 *
 * Data: `GET/PUT /api/v1/workspace/profile`. The score (0–1000), its five
 * components, zone and insight are computed server-side; the browser only
 * renders them. Locked fields come from the authenticated account.
 */

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";

import { api } from "@/lib/api/client";
import type { FinancialHealthResult, ProfileResponse } from "@/lib/api/workspaceTypes";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  emptyProfileForm,
  fieldLabel,
  formToPayload,
  GAUGE,
  GAUGE_ZONES,
  gaugeArcPath,
  gaugeNeedle,
  gaugePoint,
  GOAL_FIELDS,
  primaryCtaLabel,
  PROFILE_GOALS,
  PROFILE_SECTIONS,
  profileToForm,
  scoreRowColor,
  scoreRows,
  zoneColor,
  type ProfileField,
  type ProfileFieldKey,
  type ProfileFormState,
} from "@/lib/figma-pages/clientProfileView";

const QUERY_KEY = ["workspace", "profile"] as const;
const CARD = "rounded-[var(--card-radius)] border border-[var(--border)] bg-[var(--card)] p-5";

// ── Semicircular gauge ──────────────────────────────────────────────────────
function HealthGauge({ health }: { health: FinancialHealthResult | undefined }) {
  const complete = health?.status === "complete" && typeof health.score === "number";
  const score = complete ? (health!.score as number) : null;
  const needle = score === null ? null : gaugeNeedle(score);
  const category = complete ? health!.category : null;
  const label = category ? category.toUpperCase() : "UNABLE TO CALCULATE";
  return (
    <div className="text-center">
      <svg
        width={GAUGE.width}
        height={GAUGE.height}
        viewBox={`0 0 ${GAUGE.width} ${GAUGE.height}`}
        className="mx-auto max-w-full overflow-visible"
        role="img"
        aria-label={
          score === null
            ? "Financial Health Score: Unable to calculate."
            : `Financial Health Score ${score} out of 1000, ${category}`
        }
      >
        <path d={gaugeArcPath(180, 0, 80, 112)} fill="var(--surface-2)" />
        {GAUGE_ZONES.map((z) => (
          <path key={z.label} d={gaugeArcPath(z.start, z.end, 82, 110)} fill={z.color} opacity={0.85} />
        ))}
        {[144, 108, 72, 36].map((deg) => {
          const a = gaugePoint(deg, 80);
          const b = gaugePoint(deg, 112);
          return <line key={deg} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="var(--card)" strokeWidth={3} />;
        })}
        <circle cx={GAUGE.cx} cy={GAUGE.cy} r={18} fill="var(--card)" stroke="var(--border)" strokeWidth={1.5} />
        {needle ? (
          <line x1={GAUGE.cx} y1={GAUGE.cy} x2={needle.x} y2={needle.y} stroke="var(--fg)" strokeWidth={2.5} strokeLinecap="round" />
        ) : null}
        <circle cx={GAUGE.cx} cy={GAUGE.cy} r={5} fill={needle ? "var(--fg)" : "var(--muted)"} />
        {GAUGE_ZONES.map((z) => {
          const p = gaugePoint(z.labelDeg, 125);
          return (
            <text key={z.label} x={p.x} y={p.y + 4} textAnchor="middle" fontSize={8} fill="var(--muted)" fontFamily="var(--font-mono)">
              {z.label}
            </text>
          );
        })}
        <text x={GAUGE.cx - 118} y={GAUGE.cy + 18} fontSize={9} fill="var(--muted)" fontFamily="var(--font-mono)">
          0
        </text>
        <text x={GAUGE.cx + 106} y={GAUGE.cy + 18} fontSize={9} fill="var(--muted)" fontFamily="var(--font-mono)">
          1000
        </text>
      </svg>
      <div className="-mt-2">
        <div className="font-[family-name:var(--font-display)] text-[52px] font-bold leading-none text-[var(--fg)]">
          {score === null ? "—" : score}
        </div>
        <div className="mt-0.5 font-[family-name:var(--font-mono)] text-[13px] text-[var(--muted)]">/ 1000</div>
        <div className="mt-1.5 text-[18px] font-semibold tracking-[0.08em]" style={{ color: zoneColor(category) }}>
          {label}
        </div>
        <div className="mt-1 text-xs text-[var(--muted)]">
          {score === null
            ? "Complete the mandatory fields to receive a score."
            : `Your financial health is currently ${String(category).toLowerCase()}.`}
        </div>
      </div>
    </div>
  );
}

// ── Score breakdown row ──────────────────────────────────────────────────────
function ScoreRow({ label, value, max }: { label: string; value: number | null; max: number }) {
  const pct = value === null ? 0 : (value / max) * 100;
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 text-xs text-[var(--muted)]">{label}</div>
      <div className="h-[5px] w-[120px] overflow-hidden rounded-full bg-[var(--surface-2)]" aria-hidden="true">
        <div
          className="h-full rounded-full"
          style={{ width: `${pct}%`, background: value === null ? "transparent" : scoreRowColor(value, max) }}
        />
      </div>
      <div className="w-[46px] text-right font-[family-name:var(--font-mono)] text-xs text-[var(--fg)]">
        {value === null ? "—" : `${value} / ${max}`}
      </div>
    </div>
  );
}

// ── Input helpers ────────────────────────────────────────────────────────────
function Field({
  field,
  value,
  onChange,
  error,
}: {
  field: ProfileField;
  value: string;
  onChange: (v: string) => void;
  error?: string;
}) {
  const id = `profile-${field.key}`;
  const prefix = field.kind === "money" ? "₹" : undefined;
  return (
    <div>
      <div className="mb-[5px] flex justify-between">
        <label htmlFor={id} className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.06em] text-[var(--muted)]">
          {field.label}
          {field.optional ? <span className="ml-1.5 text-[10px] opacity-60">(optional)</span> : null}
        </label>
        {field.locked ? (
          <span className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.04em] text-[var(--c-cashflow)]">
            From your account
          </span>
        ) : null}
      </div>
      <div className="relative">
        {prefix ? (
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 font-[family-name:var(--font-mono)] text-sm text-[var(--muted)]">
            {prefix}
          </span>
        ) : null}
        <input
          id={id}
          name={field.key}
          type={field.kind === "int" ? "number" : "text"}
          inputMode={field.kind === "text" ? undefined : "numeric"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
          disabled={field.locked}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : field.hint ? `${id}-hint` : undefined}
          className={`box-border w-full rounded-lg border text-[13px] outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
            prefix ? "py-2.5 pl-7 pr-3" : "px-3 py-2.5"
          } ${
            field.locked
              ? "cursor-default border-[color-mix(in_srgb,var(--border)_50%,transparent)] bg-[color-mix(in_srgb,var(--surface-2)_60%,transparent)] text-[var(--muted)] opacity-70"
              : "border-[var(--border)] bg-[var(--surface-2)] text-[var(--fg)]"
          }`}
        />
      </div>
      {error ? (
        <div id={`${id}-error`} className="mt-1 text-[10px] text-[var(--c-risk)]">
          {error}
        </div>
      ) : field.hint ? (
        <div id={`${id}-hint`} className="mt-1 text-[10px] text-[var(--muted)]">
          {field.hint}
        </div>
      ) : null}
    </div>
  );
}

function SectionCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className={`${CARD} mb-4`} aria-label={title}>
      <h3 className="m-0 mb-4 text-[15px] font-semibold text-[var(--fg)]">{title}</h3>
      <div className="flex flex-col gap-4">{children}</div>
    </section>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────
export function ClientProfile() {
  const { session } = useAuth();
  const token = session?.accessToken;
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ProfileFormState>(() => emptyProfileForm());
  const [errors, setErrors] = useState<Partial<Record<ProfileFieldKey, string>>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [showInvestments, setShowInvestments] = useState(false);
  const [dirty, setDirty] = useState(false);

  const profileQuery = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => api.workspaceProfile({ token }),
    enabled: Boolean(token),
    retry: false,
    staleTime: 30_000,
  });
  const data = profileQuery.data;

  useEffect(() => {
    if (data && !dirty) {
      const next = profileToForm(data.profile);
      setForm(next);
      if (next.investments.length) setShowInvestments(true);
    }
  }, [data, dirty]);

  const save = useMutation({
    mutationFn: (payload: Parameters<typeof api.workspaceProfileSave>[0]) =>
      api.workspaceProfileSave(payload, { token }),
    onSuccess: (next: ProfileResponse) => {
      queryClient.setQueryData(QUERY_KEY, next);
      setDirty(false);
      setServerError(null);
    },
    onError: (err: unknown) => setServerError(err instanceof Error ? err.message : "Unable to save."),
  });

  const health = data?.health;
  const completeness = data?.completeness;
  const rows = useMemo(() => scoreRows(health), [health]);

  const setValue = (key: ProfileFieldKey, v: string) => {
    setDirty(true);
    setForm((f) => ({ ...f, values: { ...f.values, [key]: v } }));
    if (errors[key]) setErrors((e) => ({ ...e, [key]: undefined }));
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const result = formToPayload(form);
    if (!result.ok) {
      setErrors(result.errors);
      return;
    }
    setErrors({});
    save.mutate(result.payload);
  };

  const renderField = (f: ProfileField) => (
    <Field key={f.key} field={f} value={form.values[f.key]} onChange={(v) => setValue(f.key, v)} error={errors[f.key]} />
  );

  if (!token) {
    return (
      <div className="px-7 py-6">
        <h1 className="m-0 font-[family-name:var(--font-display)] text-2xl font-medium tracking-[-0.01em] text-[var(--fg)]">
          Your Financial Profile
        </h1>
        <p className="mt-1 text-[13px] text-[var(--muted)]">
          Sign in to build your profile. Scores are calculated on the server from your inputs and never estimated.
        </p>
        <Link href="/login" className="mt-4 inline-block text-xs text-[var(--c-dsp)] hover:underline">
          Sign in →
        </Link>
      </div>
    );
  }

  const percent = completeness?.percent ?? 0;

  return (
    <div className="h-full overflow-y-auto bg-[var(--bg)]">
      {/* Top bar */}
      <div className="px-7 pt-6">
        <div className="flex flex-wrap items-end justify-between gap-3 pb-4">
          <div>
            <h1 className="m-0 font-[family-name:var(--font-display)] text-2xl font-medium tracking-[-0.01em] text-[var(--fg)]">
              Your Financial Profile
            </h1>
            <p className="m-0 mt-1 text-[13px] text-[var(--muted)]">Help us understand your current financial health.</p>
          </div>
          <div className="flex items-center gap-2.5 pb-1" aria-live="polite">
            <div className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.04em] text-[var(--muted)]">
              {profileQuery.isPending ? "Loading profile…" : `Profile ${percent}% complete`}
            </div>
            <div
              className="h-[5px] w-[100px] overflow-hidden rounded-full bg-[var(--surface-2)]"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={percent}
              aria-label="Profile completeness"
            >
              <div className="h-full rounded-full bg-[var(--c-cashflow)]" style={{ width: `${percent}%` }} />
            </div>
          </div>
        </div>
      </div>

      {/* Two-column body */}
      <form onSubmit={submit} className="grid gap-6 px-7 pb-8 lg:grid-cols-[1fr_360px]" noValidate>
        {/* ── LEFT: Form ── */}
        <div>
          {PROFILE_SECTIONS.map((section) => (
            <SectionCard key={section.title} title={section.title}>
              <div className="grid gap-4 sm:grid-cols-2">{section.fields.map(renderField)}</div>
              {section.title === "Savings & Investments" ? (
                <>
                  <button
                    type="button"
                    onClick={() => setShowInvestments((s) => !s)}
                    className="text-left text-xs text-[var(--c-dsp)] hover:underline"
                    aria-expanded={showInvestments}
                  >
                    + Add investment details
                  </button>
                  {showInvestments ? (
                    <div className="flex flex-col gap-2" aria-label="Investment details">
                      {form.investments.map((row, i) => (
                        <div key={i} className="grid gap-2 sm:grid-cols-[1fr_120px_140px_auto]">
                          <input
                            aria-label={`Investment ${i + 1} name`}
                            placeholder="e.g. Nifty 50 index fund"
                            value={row.label}
                            onChange={(e) => {
                              setDirty(true);
                              setForm((f) => {
                                const inv = [...f.investments];
                                inv[i] = { ...inv[i], label: e.target.value };
                                return { ...f, investments: inv };
                              });
                            }}
                            className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-[13px] text-[var(--fg)]"
                          />
                          <input
                            aria-label={`Investment ${i + 1} type`}
                            placeholder="Stocks / MF / FD"
                            value={row.kind}
                            onChange={(e) => {
                              setDirty(true);
                              setForm((f) => {
                                const inv = [...f.investments];
                                inv[i] = { ...inv[i], kind: e.target.value };
                                return { ...f, investments: inv };
                              });
                            }}
                            className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-[13px] text-[var(--fg)]"
                          />
                          <input
                            aria-label={`Investment ${i + 1} amount in rupees`}
                            placeholder="₹ amount"
                            inputMode="numeric"
                            value={row.amount}
                            onChange={(e) => {
                              setDirty(true);
                              setForm((f) => {
                                const inv = [...f.investments];
                                inv[i] = { ...inv[i], amount: e.target.value };
                                return { ...f, investments: inv };
                              });
                            }}
                            className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 font-[family-name:var(--font-mono)] text-[13px] text-[var(--fg)]"
                          />
                          <button
                            type="button"
                            aria-label={`Remove investment ${i + 1}`}
                            onClick={() => {
                              setDirty(true);
                              setForm((f) => ({ ...f, investments: f.investments.filter((_, j) => j !== i) }));
                            }}
                            className="rounded-lg border border-[var(--border)] px-2 text-xs text-[var(--muted)] hover:text-[var(--c-risk)]"
                          >
                            ×
                          </button>
                        </div>
                      ))}
                      <button
                        type="button"
                        onClick={() => {
                          setDirty(true);
                          setForm((f) => ({ ...f, investments: [...f.investments, { label: "", kind: "", amount: "" }] }));
                        }}
                        className="self-start rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs text-[var(--muted)] hover:text-[var(--fg)]"
                      >
                        Add row
                      </button>
                    </div>
                  ) : null}
                </>
              ) : null}
              {section.title === "Debt & Protection" ? (
                <label className="flex cursor-pointer items-center gap-2 text-xs text-[var(--muted)]">
                  <input
                    type="checkbox"
                    checked={form.noOutstandingDebt}
                    onChange={(e) => {
                      setDirty(true);
                      setForm((f) => ({ ...f, noOutstandingDebt: e.target.checked }));
                    }}
                    style={{ accentColor: "var(--c-dsp)" }}
                  />
                  No outstanding debt
                </label>
              ) : null}
            </SectionCard>
          ))}

          {/* 5. Financial Goal */}
          <SectionCard title="Primary Financial Goal">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4" role="radiogroup" aria-label="Primary financial goal">
              {PROFILE_GOALS.map((g) => {
                const active = form.primaryGoal === g.id;
                return (
                  <button
                    key={g.id}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => {
                      setDirty(true);
                      setForm((f) => ({ ...f, primaryGoal: g.id }));
                    }}
                    className={`rounded-[10px] border px-2 py-2.5 text-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                      active
                        ? "border-[var(--c-dsp)] bg-[color-mix(in_srgb,var(--c-dsp)_15%,transparent)]"
                        : "border-[var(--border)] bg-[var(--surface-2)]"
                    }`}
                  >
                    <div className="mb-1 text-[18px]" aria-hidden="true">
                      {g.icon}
                    </div>
                    <div className={`text-[10px] leading-[1.3] ${active ? "text-[var(--fg)]" : "text-[var(--muted)]"}`}>{g.label}</div>
                  </button>
                );
              })}
            </div>
            <div className="mt-1 grid gap-4 sm:grid-cols-2">{GOAL_FIELDS.map(renderField)}</div>
          </SectionCard>

          {/* CTAs */}
          <div className="mt-1 flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={save.isPending}
              className="flex-1 rounded-[10px] bg-[var(--c-dsp)] px-4 py-3.5 text-sm font-semibold text-white hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:opacity-60"
            >
              {save.isPending ? "Saving…" : primaryCtaLabel(health)}
            </button>
            <button
              type="button"
              disabled={save.isPending}
              onClick={() => {
                const result = formToPayload(form);
                if (result.ok) save.mutate(result.payload);
                else setErrors(result.errors);
              }}
              className="rounded-[10px] border border-[var(--border)] px-5 py-3.5 text-[13px] text-[var(--muted)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:opacity-60"
            >
              Save &amp; Continue Later
            </button>
          </div>
          {serverError ? (
            <p role="alert" className="mt-2 text-xs text-[var(--c-risk)]">
              {serverError}
            </p>
          ) : null}
          {profileQuery.isError ? (
            <p role="alert" className="mt-2 text-xs text-[var(--c-risk)]">
              Data unavailable. The profile service did not respond.
            </p>
          ) : null}
        </div>

        {/* ── RIGHT: Score card ── */}
        <div className="lg:sticky lg:top-6 lg:self-start">
          <div className={`${CARD} mb-4`}>
            <div className="mb-2 text-center">
              <div className="mb-0.5 font-[family-name:var(--font-mono)] text-[11px] tracking-[0.07em] text-[var(--muted)]">
                FINANCIAL HEALTH SCORE
              </div>
              <div className="text-[10px] text-[var(--muted)]">An overall view of your current financial position.</div>
            </div>
            <HealthGauge health={health} />
            {health?.status === "incomplete" && health.missing_inputs.length ? (
              <p className="mt-3 text-[11px] text-[var(--muted)]">
                Needs: {health.missing_inputs.map(fieldLabel).join(" · ")}
              </p>
            ) : null}
          </div>

          <div className={`${CARD} mb-4`}>
            <h4 className="m-0 mb-3.5 text-[13px] font-semibold text-[var(--fg)]">What influences your score?</h4>
            <div className="flex flex-col gap-3">
              {rows.map((r) => (
                <ScoreRow key={r.label} label={r.label} value={r.value} max={r.max} />
              ))}
            </div>
            {health?.status === "complete" ? (
              <details className="mt-3 text-[10px] text-[var(--muted)]">
                <summary className="cursor-pointer">How each component is calculated</summary>
                <ul className="m-0 mt-2 flex list-none flex-col gap-1 p-0">
                  {health.components.map((c) => (
                    <li key={c.key}>
                      <span className="text-[var(--fg)]">{c.label}:</span> {c.formula}. {c.note}
                    </li>
                  ))}
                </ul>
                <p className="mt-2">Score = Σ components × 2 · {health.version}</p>
              </details>
            ) : null}
          </div>

          <div className="rounded-[var(--card-radius)] border border-[color-mix(in_srgb,var(--c-cashflow)_25%,transparent)] bg-[color-mix(in_srgb,var(--c-cashflow)_8%,var(--card))] p-5">
            <div className="mb-2 text-[13px] font-semibold text-[var(--fg)]">
              {health?.status === "complete" ? `Your financial position is ${String(health.category).toLowerCase()}.` : "No score yet."}
            </div>
            <div className="text-xs leading-[1.6] text-[var(--muted)]">
              {health?.insight ?? "Complete the mandatory fields and calculate to receive a server-computed insight."}
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}

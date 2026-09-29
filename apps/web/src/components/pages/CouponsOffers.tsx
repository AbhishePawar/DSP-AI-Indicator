"use client";

/**
 * Figma `Coupons.tsx` — header + search · stats bar · featured banner ·
 * category filter chips · coupon grid with copy-to-clipboard · T&C note.
 *
 * Data: `GET /api/v1/saas/coupons` (administrator-provisioned coupon metadata
 * from the SaaS overlay). Nothing is invented: when no coupon is published the
 * page states so. The Figma referral programme (personal link, savings totals)
 * has no backing service and is omitted rather than fabricated.
 */

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { FigmaPage, PanelEmpty, PillButton } from "@/components/pages/PagePrimitives";
import { api } from "@/lib/api/client";
import type { Coupon, CouponCategory } from "@/lib/api/workspaceTypes";
import { useAuth } from "@/lib/auth/AuthProvider";

const QUERY_KEY = ["saas", "coupons"] as const;

type Filter = "all" | CouponCategory;
const FILTERS: { label: string; value: Filter }[] = [
  { label: "All Offers", value: "all" },
  { label: "Premium Plans", value: "premium" },
  { label: "Research", value: "research" },
  { label: "Analysis", value: "analysis" },
  { label: "Referral", value: "referral" },
];
const CATEGORY_COLOR: Record<CouponCategory, string> = {
  premium: "var(--c-dsp)",
  research: "var(--c-revenue)",
  analysis: "var(--c-cashflow)",
  referral: "var(--c-profit)",
};
const CATEGORY_LABEL: Record<CouponCategory, string> = {
  premium: "Premium",
  research: "Research",
  analysis: "Analysis",
  referral: "Referral",
};

export function discountText(c: Coupon): string {
  if (c.discount_label) return c.discount_label;
  if (c.discount_type === "free") return "Free";
  if (c.discount_type === "flat") return typeof c.discount_pct === "number" ? `₹${c.discount_pct}` : "Offer";
  return typeof c.discount_pct === "number" ? `${c.discount_pct}%` : "Offer";
}

export function daysLeft(expiresAt: string | null, now = Date.now()): number | null {
  if (!expiresAt) return null;
  const t = Date.parse(expiresAt);
  if (!Number.isFinite(t)) return null;
  return Math.max(0, Math.ceil((t - now) / 86_400_000));
}

function expiryLabel(expiresAt: string | null): string {
  if (!expiresAt) return "Ongoing";
  const t = Date.parse(expiresAt);
  if (!Number.isFinite(t)) return expiresAt;
  return new Date(t).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function CopyCodeButton({ code, prominent }: { code: string; prominent?: boolean }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }
  return (
    <button
      type="button"
      onClick={copy}
      aria-label={copied ? `Copied ${code}` : `Copy coupon code ${code}`}
      className={
        prominent
          ? "inline-flex min-h-10 items-center gap-2.5 rounded-[10px] px-5 text-white transition-colors"
          : "inline-flex min-h-9 items-center gap-2 rounded-lg border px-3.5 transition-colors"
      }
      style={
        prominent
          ? { background: copied ? "color-mix(in srgb, var(--c-profit) 15%, transparent)" : "var(--c-dsp)", color: copied ? "var(--c-profit)" : "#fff" }
          : {
              background: copied ? "color-mix(in srgb, var(--c-profit) 12%, transparent)" : "var(--surface-2)",
              borderColor: copied ? "color-mix(in srgb, var(--c-profit) 35%, transparent)" : "var(--border)",
              color: copied ? "var(--c-profit)" : "var(--fg)",
            }
      }
    >
      <span className="font-[family-name:var(--font-mono)] text-[13px] font-semibold tracking-[0.08em]">{code}</span>
      <span className="text-xs">{copied ? "✓ Copied" : "Copy code"}</span>
    </button>
  );
}

function Tag({ children, color }: { children: string; color: string }) {
  return (
    <span
      className="rounded-full border px-2 py-0.5 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.06em]"
      style={{ color, borderColor: `color-mix(in srgb, ${color} 20%, transparent)`, background: `color-mix(in srgb, ${color} 10%, transparent)` }}
    >
      {children}
    </span>
  );
}

function CouponCard({ coupon }: { coupon: Coupon }) {
  const color = CATEGORY_COLOR[coupon.category] ?? "var(--c-dsp)";
  const days = daysLeft(coupon.expires_at);
  const expiringSoon = days !== null && days <= 10;
  return (
    <article className="flex flex-col overflow-hidden rounded-[var(--card-radius)] border border-[var(--border)] bg-[var(--card)]" aria-label={coupon.title ?? coupon.code}>
      <div className="h-[3px]" style={{ background: `linear-gradient(90deg, ${color}, color-mix(in srgb, ${color} 55%, transparent))` }} aria-hidden="true" />
      <div className="border-b border-[var(--border)] px-5 pb-3.5 pt-4">
        <div className="mb-2.5 flex items-start justify-between gap-2.5">
          <div className="flex flex-wrap gap-1.5">
            <Tag color={color}>{CATEGORY_LABEL[coupon.category]?.toUpperCase() ?? coupon.category.toUpperCase()}</Tag>
            {expiringSoon ? <Tag color="var(--c-risk)">EXPIRING SOON</Tag> : null}
          </div>
          <div className="shrink-0 font-[family-name:var(--font-heading)] text-[22px] font-semibold tracking-tight" style={{ color }}>
            {discountText(coupon)}
          </div>
        </div>
        <h3 className="font-[family-name:var(--font-heading)] text-base font-medium leading-snug text-[var(--fg)]">
          {coupon.title ?? coupon.code}
        </h3>
        {coupon.description ? <p className="mt-1.5 text-xs leading-relaxed text-[var(--muted)]">{coupon.description}</p> : null}
      </div>
      {coupon.applicable_to.length ? (
        <div className="flex flex-wrap gap-1.5 border-b border-[var(--border)] px-5 py-2.5">
          {coupon.applicable_to.map((a) => (
            <span key={a} className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2 py-0.5 font-[family-name:var(--font-mono)] text-[10px] text-[var(--muted)]">
              {a}
            </span>
          ))}
        </div>
      ) : null}
      <div className="mt-auto flex items-center justify-between gap-2.5 px-5 py-3">
        <div>
          <p className="mb-0.5 font-[family-name:var(--font-mono)] text-[9px] tracking-[0.08em] text-[var(--muted)]">{days === null ? "VALID" : "EXPIRES"}</p>
          <p className="font-[family-name:var(--font-mono)] text-xs font-medium" style={{ color: expiringSoon ? "var(--c-risk)" : "var(--muted)" }}>
            {expiryLabel(coupon.expires_at)}
          </p>
          {days !== null ? (
            <p className="font-[family-name:var(--font-mono)] text-[10px]" style={{ color: expiringSoon ? "var(--c-risk)" : "var(--muted)" }}>
              {days} day{days === 1 ? "" : "s"} left
            </p>
          ) : null}
        </div>
        <CopyCodeButton code={coupon.code} />
      </div>
      {coupon.min_spend !== null && coupon.min_spend !== undefined && coupon.min_spend !== "" ? (
        <p className="px-5 pb-3 font-[family-name:var(--font-mono)] text-[10px] text-[var(--muted)]">
          Min. spend {typeof coupon.min_spend === "number" ? `₹${coupon.min_spend.toLocaleString("en-IN")}` : coupon.min_spend}
        </p>
      ) : null}
    </article>
  );
}

function FeaturedBanner({ coupon }: { coupon: Coupon }) {
  const days = daysLeft(coupon.expires_at);
  return (
    <section className="relative overflow-hidden rounded-2xl border border-[color-mix(in_srgb,var(--c-dsp)_35%,transparent)] bg-[var(--card)]" aria-label="Featured offer">
      <div className="pointer-events-none absolute inset-0" style={{ background: "radial-gradient(ellipse 60% 80% at 100% 50%, color-mix(in srgb, var(--c-dsp) 8%, transparent) 0%, transparent 70%)" }} aria-hidden="true" />
      <div className="relative flex flex-wrap items-center justify-between gap-6 px-6 py-7 sm:px-8">
        <div className="min-w-[240px] flex-1">
          <p className="mb-3 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.1em] text-[var(--c-dsp)]">FEATURED OFFER</p>
          <h2 className="font-[family-name:var(--font-heading)] text-[clamp(20px,3vw,28px)] font-medium tracking-tight text-[var(--fg)]">
            {coupon.title ?? coupon.code}
          </h2>
          {coupon.description ? <p className="mt-2 max-w-md text-[13px] leading-relaxed text-[var(--muted)]">{coupon.description}</p> : null}
          {coupon.applicable_to.length ? (
            <div className="mt-4 flex flex-wrap gap-1.5">
              {coupon.applicable_to.map((a) => (
                <span key={a} className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2.5 py-0.5 font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)]">{a}</span>
              ))}
            </div>
          ) : null}
          <div className="mt-4 flex flex-wrap items-center gap-2.5">
            <CopyCodeButton code={coupon.code} prominent />
            <span className="font-[family-name:var(--font-mono)] text-xs text-[var(--muted)]">
              {days === null ? "Ongoing" : `Expires ${expiryLabel(coupon.expires_at)} · ${days} day${days === 1 ? "" : "s"} left`}
            </span>
          </div>
        </div>
        <div className="shrink-0 text-center">
          <div className="font-[family-name:var(--font-heading)] text-[clamp(52px,8vw,80px)] font-semibold leading-none tracking-tighter text-[var(--c-dsp)]">
            {discountText(coupon)}
          </div>
          <p className="mt-1 font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)]">OFF YOUR PLAN</p>
        </div>
      </div>
    </section>
  );
}

export function CouponsOffers() {
  const { session } = useAuth();
  const token = session?.accessToken;
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");

  const couponsQuery = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => api.coupons({ token }),
    enabled: Boolean(token),
    retry: false,
    staleTime: 60_000,
  });

  const couponsData = couponsQuery.data?.result?.coupons;
  const coupons = useMemo<Coupon[]>(() => couponsData ?? [], [couponsData]);
  const featured = coupons.find((c) => c.featured) ?? null;
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return coupons.filter((c) => {
      if (featured && c.code === featured.code) return false;
      if (filter !== "all" && c.category !== filter) return false;
      if (!q) return true;
      return c.code.toLowerCase().includes(q) || (c.title ?? "").toLowerCase().includes(q);
    });
  }, [coupons, featured, filter, query]);

  const expiringSoon = coupons.filter((c) => {
    const d = daysLeft(c.expires_at);
    return d !== null && d <= 10;
  }).length;
  const bestPct = coupons.reduce<number | null>((best, c) => {
    if (c.discount_type !== "percent" || typeof c.discount_pct !== "number") return best;
    return best === null ? c.discount_pct : Math.max(best, c.discount_pct);
  }, null);

  const stats = [
    { label: "ACTIVE OFFERS", value: couponsQuery.isSuccess ? String(coupons.length) : "—", color: "var(--c-dsp)" },
    { label: "EXPIRING SOON", value: couponsQuery.isSuccess ? String(expiringSoon) : "—", color: "var(--c-risk)" },
    { label: "CATEGORIES", value: couponsQuery.isSuccess ? String(new Set(coupons.map((c) => c.category)).size) : "—", color: "var(--muted)" },
    { label: "BEST DISCOUNT", value: bestPct === null ? "—" : `${bestPct}%`, color: "var(--c-profit)" },
  ];

  return (
    <FigmaPage
      title="Coupons & Client Offers"
      subtitle="Active discounts and promotions on your DSP subscriptions and services."
      gap={24}
      actions={
        <label className="flex min-h-10 min-w-[220px] items-center gap-2 rounded-[9px] border border-[var(--border)] bg-[var(--surface-2)] px-3.5">
          <span className="sr-only">Search offers or codes</span>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <circle cx="6" cy="6" r="4" stroke="var(--muted)" strokeWidth="1.3" />
            <line x1="9.5" y1="9.5" x2="12.5" y2="12.5" stroke="var(--muted)" strokeWidth="1.3" strokeLinecap="round" />
          </svg>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search offers or codes…"
            className="min-w-0 flex-1 bg-transparent text-[13px] text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none"
          />
        </label>
      }
    >
      <div className="grid grid-cols-2 overflow-hidden rounded-xl border border-[var(--border)] sm:grid-cols-4" role="list" aria-label="Offer statistics">
        {stats.map((s, i) => (
          <div key={s.label} role="listitem" className={`bg-[var(--card)] px-5 py-4 text-center ${i > 0 ? "border-l border-[var(--border)]" : ""} ${i >= 2 ? "border-t border-[var(--border)] sm:border-t-0" : ""}`}>
            <div className="mb-1.5 font-[family-name:var(--font-heading)] text-[28px] font-semibold leading-none" style={{ color: s.color }}>{s.value}</div>
            <div className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.07em] text-[var(--muted)]">{s.label}</div>
          </div>
        ))}
      </div>

      {!token ? (
        <PanelEmpty title="Sign in required." description="Offers are shown to signed-in DSP users." />
      ) : couponsQuery.isPending ? (
        <PanelEmpty title="Loading offers…" />
      ) : couponsQuery.isError ? (
        <PanelEmpty
          title="Offers unavailable."
          description={couponsQuery.error instanceof Error ? couponsQuery.error.message : "The offers service did not respond."}
          action={
            <button type="button" onClick={() => couponsQuery.refetch()} className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs text-[var(--fg)]">Retry</button>
          }
        />
      ) : coupons.length === 0 ? (
        <PanelEmpty title="No offers published." description="No coupon is currently published by the DSP administrators. Nothing is fabricated; check back later." />
      ) : (
        <>
          {featured ? <FeaturedBanner coupon={featured} /> : null}

          <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter offers by category">
            {FILTERS.map((f) => (
              <PillButton key={f.value} active={filter === f.value} onClick={() => setFilter(f.value)}>
                {f.label}
              </PillButton>
            ))}
            <span className="ml-auto font-[family-name:var(--font-mono)] text-xs text-[var(--muted)]" aria-live="polite">
              {filtered.length} offer{filtered.length === 1 ? "" : "s"}
            </span>
          </div>

          {filtered.length ? (
            <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]">
              {filtered.map((c) => <CouponCard key={c.code} coupon={c} />)}
            </div>
          ) : (
            <PanelEmpty title="No offers found" description="Try a different filter or search term." />
          )}
        </>
      )}

      <section className="rounded-[10px] border border-[var(--border)] bg-[var(--surface-2)] px-5 py-4" aria-label="Terms and conditions">
        <p className="mb-1 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.07em] text-[var(--muted)]">TERMS & CONDITIONS</p>
        <p className="text-xs leading-relaxed text-[var(--muted)]">
          Coupons are valid for the period shown and cannot be combined unless stated. Each coupon may only be applied once per account per billing cycle. Coupon metadata only — no payment is applied without the billing provider. DSP reserves the right to withdraw any offer without prior notice.
        </p>
      </section>
    </FigmaPage>
  );
}

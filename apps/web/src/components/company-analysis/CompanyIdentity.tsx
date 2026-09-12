import type { CompanyEntry } from "@/lib/companies/catalogue";

export type CompanyIdentityData = {
  symbol: string;
  company?: string | null;
  exchange?: string | null;
  isin?: string | null;
};

export function CompanyIdentity({
  identity,
  catalogue,
  status,
}: {
  identity: CompanyIdentityData;
  catalogue?: CompanyEntry;
  status?: "researching" | "ready" | "unavailable";
}) {
  const company = identity.company || catalogue?.name || "Company research";
  const symbol = identity.symbol || catalogue?.ticker || "—";
  const exchange = identity.exchange || catalogue?.exchange;
  const isin = identity.isin;
  const metadata = [symbol, exchange, isin].filter(Boolean).join(" · ");

  return (
    <section
      aria-labelledby="company-identity-title"
      className="border-b border-[var(--border)] bg-[var(--surface)] px-4 py-5 sm:px-6"
    >
      <div className="mx-auto flex max-w-5xl flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">
            Company research
          </p>
          <h1
            id="company-identity-title"
            className="mt-2 truncate font-[family-name:var(--font-display)] text-2xl font-medium tracking-tight text-[var(--fg)] sm:text-3xl"
          >
            {company}
          </h1>
          <p className="mt-1 truncate font-mono text-xs text-[var(--muted)] sm:text-sm">
            {metadata || symbol}
          </p>
        </div>
        <p className="shrink-0 text-sm text-[var(--muted)]" role="status" aria-live="polite">
          {status === "researching"
            ? `Researching ${symbol}…`
            : status === "unavailable"
              ? "Research unavailable"
              : "DSP analysis workspace"}
        </p>
      </div>
    </section>
  );
}

export function CompanyIdentityUnavailable() {
  return (
    <section className="border-b border-[var(--border)] bg-[var(--surface)] px-4 py-5 sm:px-6">
      <div className="mx-auto max-w-5xl">
        <h1 className="font-[family-name:var(--font-display)] text-xl font-medium text-[var(--fg)]">
          Search for a company to begin
        </h1>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Choose a security from the live search before starting DSP research.
        </p>
      </div>
    </section>
  );
}

export function CompanyIdentityResearching({ identity, catalogue }: { identity: CompanyIdentityData; catalogue?: CompanyEntry }) {
  return <CompanyIdentity identity={identity} catalogue={catalogue} status="researching" />;
}

"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";

/** RC3-003 — section labels only; navigation requires an explicit ticker. */
const CATEGORIES = [
  { label: "Valuation", hash: "valuation" },
  { label: "Business Quality", hash: "business-quality" },
  { label: "Financial Strength", hash: "financial-strength" },
  { label: "Management Quality", hash: "management" },
  { label: "Earnings Quality", hash: "earnings" },
  { label: "Growth Quality", hash: "growth" },
  { label: "Investment Committee", hash: "committee" },
] as const;

export function ResearchHome() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  function onSearch(e: FormEvent) {
    e.preventDefault();
    const ticker = query.trim().toUpperCase();
    if (!ticker) return;
    router.push(`/research/${encodeURIComponent(ticker)}`);
  }

  const ticker = query.trim().toUpperCase();

  return (
    <div>
      <PageHeader
        title="Company Research"
        description="Structured research views over composition pipeline results. Analyse once, review all intelligence."
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Quick Search"
            description="UI only — navigates to research by ticker. No company is pre-selected."
          />
          <CardBody>
            <form onSubmit={onSearch} className="flex flex-wrap gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter ticker"
                aria-label="Ticker search"
                className="min-w-[12rem] flex-1"
              />
              <Button type="submit" disabled={!ticker}>
                Open Research
              </Button>
            </form>
            <p className="mt-3 text-xs text-[var(--muted)]">
              Tip: run analysis in{" "}
              <Link href="/analysis" className="underline">
                Company Analysis
              </Link>{" "}
              first, then open Research Reports or classic research for that
              ticker.
            </p>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Primary journey" />
          <CardBody className="space-y-2">
            <Link href="/analysis">
              <Button variant="secondary" className="w-full">
                Company Analysis
              </Button>
            </Link>
            <Link href="/research/institutional">
              <Button variant="ghost" className="w-full">
                Research Reports
              </Button>
            </Link>
          </CardBody>
        </Card>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <PlaceholderCard
          title="Recent Analyses"
          description="Placeholder — session history coming later"
        />
        <PlaceholderCard
          title="Pinned Companies"
          description="Placeholder — pin favourites in a later epic"
        />
        <PlaceholderCard
          title="Recently Viewed"
          description="Placeholder — browse history coming later"
        />
      </div>

      <section className="mt-6" aria-label="Research categories">
        <Card>
          <CardHeader
            title="Research Categories"
            description={
              ticker
                ? `Jump into ${ticker} research sections`
                : "Enter a ticker above, then open a research section"
            }
          />
          <CardBody>
            <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {CATEGORIES.map((cat) => (
                <li key={cat.label}>
                  {ticker ? (
                    <Link
                      href={`/research/${encodeURIComponent(ticker)}#${cat.hash}`}
                      className="flex items-center gap-2 rounded-md border border-[var(--border)] px-3 py-2 text-sm transition hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                    >
                      <span
                        className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--accent)]"
                        aria-hidden
                      />
                      {cat.label}
                    </Link>
                  ) : (
                    <span className="flex items-center gap-2 rounded-md border border-[var(--border)] px-3 py-2 text-sm text-[var(--muted)]">
                      <span
                        className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--border)]"
                        aria-hidden
                      />
                      {cat.label}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      </section>
    </div>
  );
}

function PlaceholderCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <Card>
      <CardHeader title={title} description={description} />
      <CardBody>
        <p className="text-sm text-[var(--muted)]">No items yet.</p>
      </CardBody>
    </Card>
  );
}

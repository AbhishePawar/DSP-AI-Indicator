"use client";

/**
 * Figma `ResearchHub.tsx` — "Start new research" hero · Saved Research (1fr)
 * with search · Research Templates (280px). Saved research is this
 * session's real `/api/v1/analyse` history; templates are navigation
 * presets into the Company Analysis workspace. No prototype rows.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { loadRecentAnalyses } from "@/lib/analysis/recentAnalyses";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { listArchivedSessions } from "@/lib/copilot/sessionArchive";
import {
  analysisHref,
  buildSavedResearch,
  filterSavedResearch,
  mapServerSavedResearch,
  mergeSavedResearch,
  normaliseResearchSymbol,
  RESEARCH_TEMPLATES,
  type SavedResearchRow,
} from "@/lib/figma-pages/researchHubView";
import { FigmaPage, PanelEmpty } from "./PagePrimitives";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (!Number.isFinite(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

const CARD =
  "block rounded-xl border border-[var(--border)] bg-[var(--card)] transition-colors hover:border-[color-mix(in_srgb,var(--c-dsp)_40%,transparent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]";

export function ResearchHub() {
  const router = useRouter();
  const [symbolInput, setSymbolInput] = useState("");
  const [inputError, setInputError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sessionSaved, setSessionSaved] = useState<SavedResearchRow[]>([]);
  const { session } = useAuth();
  const token = session?.accessToken;

  useEffect(() => {
    setSessionSaved(buildSavedResearch(listArchivedSessions(), loadRecentAnalyses()));
  }, []);

  const serverSaved = useQuery({
    queryKey: ["workspace", "saved-research"],
    queryFn: () => api.workspaceSavedResearch({ token }),
    enabled: Boolean(token),
    retry: false,
    staleTime: 30_000,
  });

  const saved = useMemo(
    () => mergeSavedResearch(mapServerSavedResearch(serverSaved.data?.items ?? []), sessionSaved),
    [serverSaved.data, sessionSaved],
  );
  const filtered = useMemo(() => filterSavedResearch(saved, search), [saved, search]);
  const startSymbol = normaliseResearchSymbol(symbolInput);

  function startResearch(event: FormEvent) {
    event.preventDefault();
    if (!startSymbol) {
      setInputError("Enter a listed company ticker (e.g. a symbol from the Companies page).");
      return;
    }
    setInputError(null);
    router.push(analysisHref(startSymbol));
  }

  return (
    <FigmaPage title="Research Hub" subtitle="Saved analyses · Research templates" gap={24}>
      {/* Start new */}
      <section
        aria-labelledby="start-research-heading"
        className="rounded-[14px] border border-[color-mix(in_srgb,var(--c-dsp)_25%,transparent)] px-7 py-6"
        style={{
          background:
            "linear-gradient(135deg, color-mix(in srgb, var(--c-dsp) 10%, transparent) 0%, color-mix(in srgb, var(--c-cashflow) 5%, transparent) 100%)",
        }}
      >
        <h2
          id="start-research-heading"
          className="m-0 mb-2 font-[family-name:var(--font-display)] text-[22px] font-medium text-[var(--fg)]"
        >
          Start new research
        </h2>
        <p className="m-0 mb-5 text-[13px] text-[var(--muted)]">
          Enter any listed company to begin a fresh, backend-authenticated analysis.
        </p>
        <form onSubmit={startResearch} className="flex flex-wrap items-start gap-2.5">
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <label htmlFor="research-hub-symbol" className="sr-only">
              Company ticker
            </label>
            <input
              id="research-hub-symbol"
              value={symbolInput}
              onChange={(e) => {
                setSymbolInput(e.target.value);
                if (inputError) setInputError(null);
              }}
              placeholder="Company ticker…"
              autoComplete="off"
              aria-invalid={Boolean(inputError)}
              aria-describedby={inputError ? "research-hub-symbol-error" : undefined}
              className="min-h-11 w-full max-w-[320px] rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3.5 text-sm text-[var(--fg)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            />
            {inputError ? (
              <p id="research-hub-symbol-error" className="text-xs text-[var(--danger-fg)]">
                {inputError}
              </p>
            ) : null}
          </div>
          <button
            type="submit"
            aria-label="Research"
            title="Research"
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[var(--c-dsp)] px-5 text-[13px] text-white hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.9"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="8.5" cy="8.5" r="5.25" />
              <line x1="12.5" y1="12.5" x2="17" y2="17" />
            </svg>
            Research
          </button>
          <Link
            href="/companies"
            className="inline-flex min-h-11 items-center text-xs text-[var(--c-dsp)] hover:underline"
          >
            Browse companies →
          </Link>
        </form>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        {/* Saved research */}
        <section aria-labelledby="saved-research-heading">
          <div className="mb-3.5 flex items-center justify-between gap-3">
            <h3
              id="saved-research-heading"
              className="m-0 font-[family-name:var(--font-display)] text-[17px] font-medium text-[var(--fg)]"
            >
              Saved Research
            </h3>
            <label className="sr-only" htmlFor="saved-research-search">
              Search saved research
            </label>
            <input
              id="saved-research-search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search..."
              className="min-h-9 w-40 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 text-xs text-[var(--fg)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            />
          </div>
          {filtered.length === 0 ? (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--card)]">
              <PanelEmpty
                title={
                  saved.length === 0
                    ? token && serverSaved.isPending
                      ? "Loading saved research…"
                      : "No saved research yet."
                    : "No matches."
                }
                description={
                  saved.length === 0
                    ? "Research you save appears here with its tags and conversation turns; analyses you run in this session are listed too. Saved research is never pre-populated."
                    : "Try another ticker or company name."
                }
              />
            </div>
          ) : (
            <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
              {filtered.map((r) => (
                <li key={r.id}>
                  <Link href={analysisHref(r.symbol, r.exchange)} className={`${CARD} px-5 py-4`}>
                    <div className="mb-2 flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <span className="mr-2 font-[family-name:var(--font-mono)] text-[11px] text-[var(--c-dsp)]">
                          {r.symbol}
                        </span>
                        <span className="text-sm text-[var(--fg)]">{r.title}</span>
                      </div>
                      <span className="shrink-0 font-[family-name:var(--font-mono)] text-[10px] text-[var(--muted)]">
                        {formatDate(r.analysedAt)}
                      </span>
                    </div>
                    {r.tags.length ? (
                      <div className="mb-2 flex flex-wrap gap-1.5">
                        {r.tags.map((tag) => (
                          <span
                            key={tag}
                            className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-2 py-0.5 font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)]"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    <div className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)]">
                      {typeof r.turns === "number"
                        ? `${r.turns} conversation turns`
                        : r.origin === "server"
                          ? "Saved research · turns not recorded"
                          : "Backend analysis · /api/v1/analyse"}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Templates */}
        <section aria-labelledby="research-templates-heading">
          <h3
            id="research-templates-heading"
            className="m-0 mb-3.5 font-[family-name:var(--font-display)] text-[17px] font-medium text-[var(--fg)]"
          >
            Research Templates
          </h3>
          <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
            {RESEARCH_TEMPLATES.map((t) => {
              const href = startSymbol
                ? t.id === "peers"
                  ? `/analysis/compare?symbol=${encodeURIComponent(startSymbol)}`
                  : analysisHref(startSymbol)
                : null;
              const body = (
                <>
                  <div className="mb-1 text-[13px] font-medium text-[var(--fg)]">{t.title}</div>
                  <div className="mb-1.5 text-[11px] leading-relaxed text-[var(--muted)]">
                    {t.description}
                  </div>
                  <div className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--c-dsp)]">
                    {t.sections.length} sections
                  </div>
                </>
              );
              return (
                <li key={t.id}>
                  {href ? (
                    <Link href={href} className={`${CARD} rounded-[10px] px-4 py-3.5`}>
                      {body}
                    </Link>
                  ) : (
                    <div
                      className="rounded-[10px] border border-[var(--border)] bg-[var(--card)] px-4 py-3.5"
                      aria-describedby="templates-need-symbol"
                    >
                      {body}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
          <p id="templates-need-symbol" className="mt-2.5 text-[10px] text-[var(--muted)]">
            {startSymbol
              ? `Templates open ${startSymbol} in the Company Analysis workspace.`
              : "Enter a ticker above to open a template for that company."}
          </p>
        </section>
      </div>
    </FigmaPage>
  );
}

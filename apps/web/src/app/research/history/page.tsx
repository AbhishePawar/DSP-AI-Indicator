"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Trash2, ExternalLink, Clock, TrendingUp, AlertCircle } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Alert } from "@/components/ui/Alert";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  fetchResearchHistory,
  deleteResearchHistory,
  type ResearchHistoryEntry,
} from "@/lib/research/researchHistoryService";
import { saveResearchSession } from "@/lib/research/sessionStore";

function RecommendationBadge({ value }: { value: string }) {
  const upper = value.toUpperCase();
  const colorMap: Record<string, string> = {
    BUY: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30",
    STRONG_BUY: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30",
    HOLD: "bg-amber-500/15 text-amber-400 border border-amber-500/30",
    SELL: "bg-red-500/15 text-red-400 border border-red-500/30",
    STRONG_SELL: "bg-red-500/15 text-red-400 border border-red-500/30",
  };
  const cls =
    colorMap[upper] ?? "bg-[var(--surface-2)] text-[var(--muted)] border border-[var(--border)]";

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {value || "—"}
    </span>
  );
}

function HistoryRow({
  entry,
  onDelete,
  onReopen,
}: {
  entry: ResearchHistoryEntry;
  onDelete: (id: string) => void;
  onReopen: (entry: ResearchHistoryEntry) => void;
}) {
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteResearchHistory(entry.id);
      onDelete(entry.id);
    } catch {
      setDeleting(false);
    }
  }

  const savedDate = new Date(entry.savedAt);
  const formattedDate = savedDate.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
  const formattedTime = savedDate.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="flex flex-col gap-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface-1)] p-4 transition hover:border-[var(--accent)]/40 hover:bg-[var(--surface-2)]">
      {/* Header row */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex min-w-0 flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-base font-semibold text-[var(--fg)]">
              {entry.ticker}
            </span>
            {entry.exchange ? (
              <span className="text-xs text-[var(--muted)]">{entry.exchange}</span>
            ) : null}
            <RecommendationBadge value={entry.recommendation} />
          </div>
          {entry.company ? (
            <span className="truncate text-sm text-[var(--muted)]">{entry.company}</span>
          ) : null}
        </div>

        {/* Date */}
        <div className="flex shrink-0 items-center gap-1.5 text-xs text-[var(--muted)]">
          <Clock className="size-3.5" aria-hidden />
          <span>
            {formattedDate} · {formattedTime}
          </span>
        </div>
      </div>

      {/* Key findings */}
      {entry.keyFindings ? (
        <p className="line-clamp-2 text-sm text-[var(--muted)]">{entry.keyFindings}</p>
      ) : null}

      {/* Actions */}
      <div className="flex flex-wrap items-center gap-2 pt-1">
        <Button
          size="sm"
          variant="secondary"
          onClick={() => onReopen(entry)}
          disabled={!entry.request || !entry.response}
          className="gap-1.5"
        >
          <ExternalLink className="size-3.5" aria-hidden />
          Reopen
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleDelete}
          disabled={deleting}
          className="gap-1.5 text-red-400 hover:bg-red-500/10 hover:text-red-300"
          aria-label={`Delete analysis for ${entry.ticker}`}
        >
          {deleting ? (
            <Spinner size="sm" />
          ) : (
            <Trash2 className="size-3.5" aria-hidden />
          )}
          Delete
        </Button>
      </div>
    </div>
  );
}

export default function ResearchHistoryPage() {
  const { status, session } = useAuth();
  const router = useRouter();
  const [entries, setEntries] = useState<ResearchHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "restoring" || status === "loading" || status === "refreshing") return;
    if (status !== "authenticated") {
      setLoading(false);
      return;
    }

    setLoading(true);
    fetchResearchHistory()
      .then((data) => {
        setEntries(data);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load history");
      })
      .finally(() => setLoading(false));
  }, [status]);

  const handleDelete = useCallback((id: string) => {
    setEntries((prev) => prev.filter((e) => e.id !== id));
  }, []);

  const handleReopen = useCallback(
    (entry: ResearchHistoryEntry) => {
      if (!entry.request || !entry.response) return;
      saveResearchSession({
        ticker: entry.ticker,
        exchange: entry.exchange || null,
        company: entry.company || null,
        analysedAt: entry.analysedAt,
        request: entry.request as Parameters<typeof saveResearchSession>[0]["request"],
        response: entry.response as Parameters<typeof saveResearchSession>[0]["response"],
      });
      router.push(`/research/${encodeURIComponent(entry.ticker)}`);
    },
    [router],
  );

  if (status !== "authenticated" && status !== "restoring" && status !== "loading" && status !== "refreshing") {
    return (
      <div className="space-y-4">
        <PageHeader
          title="Research History"
          description="All saved company analyses — reopen or delete entries."
        />
        <Alert variant="info">Sign in to view your research history.</Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Research History"
        description="All saved company analyses — reopen or delete entries."
      />

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Spinner size="lg" />
        </div>
      ) : error ? (
        <Alert variant="error">
          <div className="flex items-center gap-2">
            <AlertCircle className="size-4 shrink-0" aria-hidden />
            <span>{error}</span>
          </div>
        </Alert>
      ) : entries.length === 0 ? (
        <Card>
          <CardBody className="flex flex-col items-center gap-3 py-12 text-center">
            <TrendingUp className="size-10 text-[var(--muted)]" aria-hidden />
            <p className="text-sm font-medium text-[var(--fg)]">No saved analyses yet</p>
            <p className="max-w-xs text-xs text-[var(--muted)]">
              Run a company analysis and save it — it will appear here for quick access.
            </p>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => router.push("/analysis")}
            >
              Go to Company Analysis
            </Button>
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-[var(--muted)]">
            {entries.length} saved {entries.length === 1 ? "analysis" : "analyses"}
          </p>
          {entries.map((entry) => (
            <HistoryRow
              key={entry.id}
              entry={entry}
              onDelete={handleDelete}
              onReopen={handleReopen}
            />
          ))}
        </div>
      )}
    </div>
  );
}

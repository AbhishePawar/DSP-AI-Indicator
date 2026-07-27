"use client";

import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { useAuth } from "@/lib/auth/AuthProvider";
import { usePersistence } from "@/providers/PersistenceProvider";

export function SavedAnalysesPanel() {
  const { status } = useAuth();
  const {
    savedAnalyses,
    deleteSavedAnalysis,
    reopenSavedAnalysis,
    saveAnalysis,
  } = usePersistence();

  if (status !== "authenticated") {
    return (
      <Card>
        <CardHeader title="Saved Analyses" />
        <CardBody className="text-sm text-[var(--muted)]">
          Sign in to save and reopen analyses across sessions.
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title="Saved Analyses"
        description="Persisted for your account — reopen restores the research session"
      />
      <CardBody>
        {savedAnalyses.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">
            No saved analyses yet. Run an analysis and use Save Analysis.
          </p>
        ) : (
          <ul className="space-y-3" aria-label="Saved analyses">
            {savedAnalyses.map((item) => (
              <li
                key={item.id}
                className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-3 last:border-0 last:pb-0"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium">
                    {item.label ?? item.company}{" "}
                    <span className="font-mono text-xs text-[var(--muted)]">
                      {item.ticker}
                    </span>
                  </p>
                  <p className="mt-0.5 text-xs text-[var(--muted)]">
                    Saved {new Date(item.savedAt).toLocaleString()} ·{" "}
                    {item.recommendation}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={!item.request || !item.response}
                    onClick={() => {
                      if (reopenSavedAnalysis(item.id)) {
                        window.location.href = `/research/${encodeURIComponent(item.ticker)}`;
                      }
                    }}
                  >
                    Reopen
                  </Button>
                  <Link href={`/research/${encodeURIComponent(item.ticker)}`}>
                    <Button size="sm" variant="ghost">
                      Research
                    </Button>
                  </Link>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => deleteSavedAnalysis(item.id)}
                  >
                    Delete
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}

export function useSaveCurrentAnalysis() {
  const { saveAnalysis } = usePersistence();
  return saveAnalysis;
}

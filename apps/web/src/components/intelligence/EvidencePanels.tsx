"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";

export function EvidencePanel({
  evidenceCounts,
  confidenceSummary,
}: {
  evidenceCounts: Record<string, number>;
  confidenceSummary: Record<string, number | null>;
}) {
  const evidenceEntries = Object.entries(evidenceCounts);
  const confEntries = Object.entries(confidenceSummary);

  return (
    <Card>
      <CardHeader
        title="Evidence Explorer"
        description="Evidence counts and confidence fields from API metadata"
      />
      <CardBody className="grid gap-6 md:grid-cols-2">
        <div>
          <h4 className="text-sm font-medium">Evidence counts</h4>
          {evidenceEntries.length ? (
            <ul className="mt-2 space-y-1 text-sm">
              {evidenceEntries.map(([k, v]) => (
                <li
                  key={k}
                  className="flex justify-between gap-3 border-b border-[var(--border)] py-1"
                >
                  <span className="text-[var(--muted)]">{k}</span>
                  <span className="font-medium">{v}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-[var(--muted)]">No evidence counts</p>
          )}
        </div>
        <div>
          <h4 className="text-sm font-medium">Component confidence</h4>
          {confEntries.length ? (
            <ul className="mt-2 space-y-1 text-sm">
              {confEntries.map(([k, v]) => (
                <li
                  key={k}
                  className="flex justify-between gap-3 border-b border-[var(--border)] py-1"
                >
                  <span className="text-[var(--muted)]">{k}</span>
                  <span className="font-medium">
                    {v === null || v === undefined
                      ? "Unavailable"
                      : `${(v * 100).toFixed(0)}%`}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-[var(--muted)]">No confidence summary</p>
          )}
        </div>
      </CardBody>
    </Card>
  );
}

export function MetricsPanel({
  strengths,
  weaknesses,
  risks,
}: {
  strengths: string[];
  weaknesses: string[];
  risks: string[];
}) {
  return (
    <Card>
      <CardHeader
        title="Strengths, Weaknesses & Risks"
        description="Derived only from API stage statuses and warnings"
      />
      <CardBody className="grid gap-4 md:grid-cols-3">
        <BulletList title="Strengths" items={strengths} />
        <BulletList title="Weaknesses" items={weaknesses} />
        <BulletList title="Risks" items={risks} />
      </CardBody>
    </Card>
  );
}

export function ExecutionMetadataPanel({
  totalElapsedMs,
  failedStage,
  packageVersions,
  executionOrder,
  limitations,
}: {
  totalElapsedMs: number | null;
  failedStage: string | null;
  packageVersions: Record<string, string>;
  executionOrder: string[];
  limitations: string[];
}) {
  return (
    <Card>
      <CardHeader
        title="Execution Metadata"
        description="Timing and package versions from the pipeline"
      />
      <CardBody className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <p className="text-xs text-[var(--muted)]">Total elapsed</p>
            <p className="font-medium">
              {totalElapsedMs === null
                ? "Unavailable"
                : `${totalElapsedMs.toFixed(1)} ms`}
            </p>
          </div>
          <div>
            <p className="text-xs text-[var(--muted)]">Failed stage</p>
            <p className="font-medium">{failedStage || "None"}</p>
          </div>
        </div>
        <div>
          <h4 className="text-sm font-medium">Execution order</h4>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {executionOrder.length ? executionOrder.join(" → ") : "Unavailable"}
          </p>
        </div>
        <div>
          <h4 className="text-sm font-medium">Package versions</h4>
          {Object.keys(packageVersions).length ? (
            <ul className="mt-2 grid gap-1 sm:grid-cols-2 text-sm">
              {Object.entries(packageVersions).map(([k, v]) => (
                <li key={k} className="flex justify-between gap-2">
                  <span className="text-[var(--muted)]">{k}</span>
                  <span className="font-mono text-xs">{v}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-1 text-sm text-[var(--muted)]">Unavailable</p>
          )}
        </div>
        {limitations.length ? (
          <div>
            <h4 className="text-sm font-medium">Limitations</h4>
            <ul className="mt-2 list-inside list-disc text-sm text-[var(--muted)]">
              {limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardBody>
    </Card>
  );
}

function BulletList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h4 className="text-sm font-medium">{title}</h4>
      {items.length ? (
        <ul className="mt-2 list-inside list-disc text-sm text-[var(--muted)]">
          {items.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-[var(--muted)]">None reported</p>
      )}
    </div>
  );
}

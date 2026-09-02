"use client";

import { memo } from "react";

import type { MethodologyPanelView, TransparencyPanelView } from "@/lib/analysis/types";
import { TraceLink } from "@/components/analysis/TraceLink";

export const MethodologyCard = memo(function MethodologyCard({
  methodology,
}: {
  methodology: MethodologyPanelView;
}) {
  return (
    <section id="methodology_panel" className="space-y-4">
      <div className="border-b border-[var(--border)] pb-3">
        <h3 className="font-[family-name:var(--font-display)] text-base tracking-tight text-[var(--fg)]">
          Methodology Panel
        </h3>
        <p className="mt-0.5 text-xs text-[var(--muted)]">
          Versions that produced this research presentation
        </p>
      </div>
      <div className="divide-y divide-[var(--border)] text-sm">
        <FieldRow label="Research methodology" text={methodology.researchMethodology} />
        <FieldRow label="Analysis version" text={methodology.analysisVersion} />
        <FieldRow label="Calculation version" text={methodology.calculationVersion} />
        <FieldRow label="Presentation version" text={methodology.presentationVersion} />
        <FieldRow label="Compliance version" text={methodology.complianceVersion} />
      </div>
      <p className="text-xs text-[var(--muted)]">
        Linked from <TraceLink href="#decision_trace">Decision Trace</TraceLink>
      </p>
    </section>
  );
});

export const TransparencyPanel = memo(function TransparencyPanel({
  panel,
}: {
  panel: TransparencyPanelView;
}) {
  return (
    <section id="transparency_panel" className="space-y-4">
      <div className="border-b border-[var(--border)] pb-3">
        <h3 className="font-[family-name:var(--font-display)] text-base tracking-tight text-[var(--fg)]">
          Transparency Panel
        </h3>
        <p className="mt-0.5 text-xs text-[var(--muted)]">
          Known unknowns, estimates, AI-generated sections, and external sources
        </p>
      </div>
      <div className="grid gap-5 sm:grid-cols-2 text-sm">
        <List label="Known unknowns" items={panel.knownUnknowns} />
        <List label="Unavailable data" items={panel.unavailableData} />
        <List label="Estimated fields" items={panel.estimatedFields} />
        <List label="AI-generated sections" items={panel.aiGeneratedSections} />
        <div className="sm:col-span-2">
          <List label="External sources" items={panel.externalSources} />
        </div>
      </div>
    </section>
  );
});

function FieldRow({ label, text }: { label: string; text: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2 first:pt-0 last:pb-0">
      <p className="text-xs text-[var(--muted)] shrink-0">{label}</p>
      <p className="text-sm font-medium text-[var(--fg)] text-right">{text}</p>
    </div>
  );
}

function List({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-2">{label}</p>
      {items.length > 0 ? (
        <ul className="space-y-1">
          {items.map((i) => (
            <li key={i} className="flex gap-2 text-sm text-[var(--muted)]">
              <span className="mt-1.5 inline-block h-1 w-1 rounded-full bg-[var(--border)] shrink-0" aria-hidden />
              {i}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-[var(--muted)]">None</p>
      )}
    </div>
  );
}

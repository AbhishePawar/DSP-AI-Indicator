"use client";

import { memo } from "react";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { MethodologyPanelView, TransparencyPanelView } from "@/lib/analysis/types";
import { TraceLink } from "@/components/analysis/TraceLink";

export const MethodologyCard = memo(function MethodologyCard({
  methodology,
}: {
  methodology: MethodologyPanelView;
}) {
  return (
    <Card id="methodology_panel">
      <CardHeader
        title="Methodology Panel"
        description="Versions that produced this research presentation"
      />
      <CardBody className="space-y-3 text-sm">
        <Field label="Research methodology" text={methodology.researchMethodology} />
        <Field label="Analysis version" text={methodology.analysisVersion} />
        <Field label="Calculation version" text={methodology.calculationVersion} />
        <Field label="Presentation version" text={methodology.presentationVersion} />
        <Field label="Compliance version" text={methodology.complianceVersion} />
        <p className="text-xs text-[var(--muted)]">
          Linked from <TraceLink href="#decision_trace">Decision Trace</TraceLink>
        </p>
      </CardBody>
    </Card>
  );
});

export const TransparencyPanel = memo(function TransparencyPanel({
  panel,
}: {
  panel: TransparencyPanelView;
}) {
  return (
    <Card id="transparency_panel">
      <CardHeader
        title="Transparency Panel"
        description="Known unknowns, estimates, AI-generated sections, and external sources"
      />
      <CardBody className="grid gap-4 sm:grid-cols-2 text-sm">
        <List label="Known unknowns" items={panel.knownUnknowns} />
        <List label="Unavailable data" items={panel.unavailableData} />
        <List label="Estimated fields" items={panel.estimatedFields} />
        <List label="AI-generated sections" items={panel.aiGeneratedSections} />
        <div className="sm:col-span-2">
          <List label="External sources" items={panel.externalSources} />
        </div>
      </CardBody>
    </Card>
  );
});

function Field({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className="mt-1">{text}</p>
    </div>
  );
}

function List({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
        {items.map((i) => (
          <li key={i}>{i}</li>
        ))}
      </ul>
    </div>
  );
}

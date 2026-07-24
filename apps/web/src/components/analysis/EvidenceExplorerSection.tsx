"use client";

import { memo, useId, useMemo, useState } from "react";

import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { EvidenceExplorerItem, EvidenceExplorerView } from "@/lib/analysis/types";
import { CATEGORY_LABELS, type ValueCategory } from "@/lib/trust/labels";
import { TraceLink } from "@/components/analysis/TraceLink";

const GROUP_ORDER: ValueCategory[] = [
  "verified_fact",
  "calculated",
  "estimated",
  "ai_interpretation",
  "external_consensus",
  "user_input",
  "unavailable",
];

export const EvidenceItem = memo(function EvidenceItem({
  item,
}: {
  item: EvidenceExplorerItem;
}) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  return (
    <article className="rounded-md border border-[var(--border)] bg-[var(--surface)]">
      <button
        type="button"
        className="flex min-h-11 w-full items-start justify-between gap-3 px-3 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
      >
        <span>
          <span className="font-medium">{item.title}</span>
          <span className="mt-1 block text-xs text-[var(--muted)]">
            {item.source} · Confidence {item.confidence}
          </span>
        </span>
        <span aria-hidden className="text-[var(--muted)]">
          {open ? "−" : "+"}
        </span>
      </button>
      {open ? (
        <div id={panelId} className="space-y-2 border-t border-[var(--border)] px-3 py-3 text-sm">
          <ValueCategoryBadge category={item.group} />
          <Field label="Source" text={item.source} />
          <Field label="Timestamp" text={item.timestamp ?? "Unavailable"} />
          <Field label="Confidence" text={item.confidence} />
          <Field label="Methodology" text={item.methodology} />
          <Field label="Detail" text={item.detail} />
        </div>
      ) : null}
    </article>
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

export const EvidenceTree = memo(function EvidenceTree({
  view,
}: {
  view: EvidenceExplorerView;
}) {
  const grouped = useMemo(() => {
    const map = new Map<ValueCategory, EvidenceExplorerItem[]>();
    for (const g of GROUP_ORDER) map.set(g, []);
    for (const item of view.items) {
      const list = map.get(item.group) ?? [];
      list.push(item);
      map.set(item.group, list);
    }
    return GROUP_ORDER.map((g) => ({
      group: g,
      label: CATEGORY_LABELS[g],
      items: map.get(g) ?? [],
    })).filter((g) => g.items.length > 0);
  }, [view.items]);

  return (
    <div className="space-y-4" role="tree" aria-label="Evidence by category">
      {grouped.map((g) => (
        <div key={g.group} role="group" aria-label={g.label}>
          <h3 className="mb-2 font-[family-name:var(--font-display)] text-lg">{g.label}</h3>
          <ul className="max-h-[28rem] space-y-2 overflow-y-auto overscroll-contain pr-1">
            {g.items.map((item) => (
              <li key={item.id} role="treeitem">
                <EvidenceItem item={item} />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
});

export function EvidenceExplorerSection({ view }: { view: EvidenceExplorerView }) {
  return (
    <Card>
      <CardHeader
        title="Evidence Explorer"
        description="Grouped by Verified Facts · Calculated · Estimated · AI Interpretation · External Consensus · User Inputs · Unavailable"
      />
      <CardBody className="space-y-3">
        <EvidenceTree view={view} />
        <p className="text-xs text-[var(--muted)]">
          Trace: <TraceLink href="#decision_trace">Decision Trace</TraceLink>
          {" · "}
          <TraceLink href="#methodology_panel">Methodology</TraceLink>
        </p>
      </CardBody>
    </Card>
  );
}

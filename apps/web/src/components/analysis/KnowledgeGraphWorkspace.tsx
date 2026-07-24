"use client";

import {
  memo,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import { TraceLink } from "@/components/analysis/TraceLink";
import { ConfidenceBadge } from "@/components/trust/ConfidenceBadge";
import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import {
  defaultGraphFilters,
  edgesForNodes,
  filterGraphNodes,
  KG_EDGE_TYPE_LABELS,
  KG_NODE_TYPE_LABELS,
  KG_TAB_LABELS,
  type GraphFilterState,
} from "@/lib/analysis/sprint5KnowledgeGraph";
import type {
  KgEdgeType,
  KgNodeType,
  KnowledgeGraphEdge,
  KnowledgeGraphNode,
  KnowledgeGraphTab,
  KnowledgeGraphView,
} from "@/lib/analysis/types";
import { CONFIDENCE_LABELS, type ConfidenceLevel } from "@/lib/trust/labels";
import { useCopilotOptional } from "@/components/analysis/copilot/CopilotContext";

const TABS = Object.keys(KG_TAB_LABELS) as KnowledgeGraphTab[];

const CONFIDENCE_COLORS: Record<ConfidenceLevel, string> = {
  very_high: "border-emerald-600 bg-emerald-50 text-emerald-900",
  high: "border-teal-600 bg-teal-50 text-teal-900",
  moderate: "border-amber-600 bg-amber-50 text-amber-950",
  low: "border-orange-600 bg-orange-50 text-orange-950",
  insufficient_evidence: "border-[var(--border)] bg-[var(--surface-2)] text-[var(--muted)]",
};

export const KnowledgeGraphWorkspace = memo(function KnowledgeGraphWorkspace({
  graph,
}: {
  graph: KnowledgeGraphView;
}) {
  const [tab, setTab] = useState<KnowledgeGraphTab>("research");
  const [filters, setFilters] = useState<GraphFilterState>(defaultGraphFilters);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showLegend, setShowLegend] = useState(false);
  const detailsRef = useRef<HTMLDivElement>(null);
  const copilot = useCopilotOptional();

  const visibleNodes = useMemo(
    () => filterGraphNodes(graph.nodes, filters, tab),
    [graph.nodes, filters, tab],
  );
  const visibleIds = useMemo(() => new Set(visibleNodes.map((n) => n.id)), [visibleNodes]);
  const visibleEdges = useMemo(
    () => edgesForNodes(graph.edges, visibleIds),
    [graph.edges, visibleIds],
  );

  const selected = useMemo(
    () => graph.nodes.find((n) => n.id === selectedId) ?? null,
    [graph.nodes, selectedId],
  );

  const related = useMemo(() => {
    if (!selected) return [];
    return selected.relatedNodeIds
      .map((id) => graph.nodes.find((n) => n.id === id))
      .filter(Boolean) as KnowledgeGraphNode[];
  }, [selected, graph.nodes]);

  const selectedEdges = useMemo(() => {
    if (!selected) return [];
    return graph.edges.filter((e) => e.from === selected.id || e.to === selected.id);
  }, [selected, graph.edges]);

  useEffect(() => {
    if (selectedId && !visibleIds.has(selectedId)) {
      setSelectedId(null);
    }
  }, [selectedId, visibleIds]);

  const onSelect = useCallback(
    (id: string) => {
      setSelectedId(id);
      copilot?.setSelectedGraphNode(id);
      // Focus management for a11y
      queueMicrotask(() => detailsRef.current?.focus());
    },
    [copilot],
  );

  if (graph.nodes.length === 0) {
    return <GraphEmptyState graph={graph} />;
  }

  return (
    <div className="space-y-4">
      <p className="rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm">
        <span className="font-medium">What you should know — </span>
        This Knowledge Graph shows how data, metrics, insights, evidence, and assumptions connect to
        the research conclusion. It is not a chat — every node is traceable.
      </p>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-[var(--muted)]">Graph version {graph.version}</p>
        <button
          type="button"
          className="min-h-11 rounded-md border border-[var(--border)] px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          aria-expanded={showLegend}
          onClick={() => setShowLegend((v) => !v)}
        >
          {showLegend ? "Hide legend" : "Show legend"}
        </button>
      </div>

      {showLegend ? <GraphLegend /> : null}

      <GraphSearchAndFilters filters={filters} onChange={setFilters} />

      <div
        role="tablist"
        aria-label="Knowledge graph domains"
        className="flex flex-wrap gap-2"
      >
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            id={`kg-tab-${t}`}
            className={`min-h-11 rounded-md border px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
              tab === t
                ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                : "border-[var(--border)] bg-[var(--surface)]"
            }`}
            onClick={() => setTab(t)}
          >
            {KG_TAB_LABELS[t]}
          </button>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-4">
          {/* Desktop canvas */}
          <div className="hidden md:block">
            <GraphCanvas
              nodes={visibleNodes}
              edges={visibleEdges}
              selectedId={selectedId}
              onSelect={onSelect}
              tab={tab}
            />
            <GraphMiniMap
              nodes={visibleNodes}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          </div>
          {/* Mobile list */}
          <div className="md:hidden">
            <GraphNodeList
              nodes={visibleNodes}
              edges={graph.edges}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          </div>
          <GraphEmptyHints graph={graph} visibleCount={visibleNodes.length} />
        </div>

        <div
          ref={detailsRef}
          tabIndex={-1}
          className="space-y-3 outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          aria-live="polite"
        >
          {selected ? (
            <>
              <NodeDetailsPanel node={selected} />
              <GraphEvidencePanel node={selected} />
              <RelatedMetricsPanel node={selected} related={related} onSelect={onSelect} />
              <GraphEdgePanel edges={selectedEdges} nodes={graph.nodes} onSelect={onSelect} />
              <GraphTracePanels node={selected} />
            </>
          ) : (
            <Card>
              <CardHeader title="Node details" description="Select a node to inspect evidence and links" />
              <CardBody className="text-sm text-[var(--muted)]">
                Use tabs, search, and filters to explore how DSP reaches conclusions.
              </CardBody>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
});

function GraphEmptyState({ graph }: { graph: KnowledgeGraphView }) {
  return (
    <Card>
      <CardHeader title="Knowledge Graph incomplete" />
      <CardBody className="space-y-3 text-sm">
        <p>{graph.emptyState.whyIncomplete}</p>
        <List title="Missing evidence" items={graph.emptyState.missingEvidence} />
        <List title="Future enrichment" items={graph.emptyState.futureEnrichment} />
      </CardBody>
    </Card>
  );
}

function GraphEmptyHints({
  graph,
  visibleCount,
}: {
  graph: KnowledgeGraphView;
  visibleCount: number;
}) {
  if (visibleCount > 0) {
    return (
      <details className="rounded-md border border-dashed border-[var(--border)] px-3 py-2 text-sm">
        <summary className="min-h-11 cursor-pointer font-medium">Why might the graph look incomplete?</summary>
        <div className="mt-2 space-y-2 text-[var(--muted)]">
          <p>{graph.emptyState.whyIncomplete}</p>
          <List title="Missing evidence" items={graph.emptyState.missingEvidence} />
          <List title="Future enrichment" items={graph.emptyState.futureEnrichment} />
        </div>
      </details>
    );
  }
  return (
    <Card>
      <CardBody className="text-sm text-[var(--muted)]">
        No nodes match the current tab/filters. Clear filters or switch tabs.
      </CardBody>
    </Card>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">{title}</p>
      <ul className="mt-1 list-disc pl-5">
        {items.map((i) => (
          <li key={i}>{i}</li>
        ))}
      </ul>
    </div>
  );
}

export function GraphLegend() {
  return (
    <Card>
      <CardHeader title="Legend" description="Node types · edge types · confidence · evidence categories" />
      <CardBody className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <p className="mb-2 text-xs font-medium uppercase text-[var(--muted)]">Node types</p>
          <ul className="space-y-1">
            {(Object.keys(KG_NODE_TYPE_LABELS) as KgNodeType[]).map((t) => (
              <li key={t}>{KG_NODE_TYPE_LABELS[t]}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-2 text-xs font-medium uppercase text-[var(--muted)]">Edge types</p>
          <ul className="space-y-1">
            {(Object.keys(KG_EDGE_TYPE_LABELS) as KgEdgeType[]).map((t) => (
              <li key={t}>{KG_EDGE_TYPE_LABELS[t]}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-2 text-xs font-medium uppercase text-[var(--muted)]">Confidence colors</p>
          <ul className="space-y-1">
            {(Object.keys(CONFIDENCE_LABELS) as ConfidenceLevel[]).map((c) => (
              <li key={c}>
                <span className={`inline-block rounded border px-2 py-0.5 text-xs ${CONFIDENCE_COLORS[c]}`}>
                  {CONFIDENCE_LABELS[c]}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-2 text-xs font-medium uppercase text-[var(--muted)]">Evidence categories</p>
          <ul className="space-y-1">
            <li>Verified Fact</li>
            <li>Calculated</li>
            <li>Estimated</li>
            <li>AI Interpretation</li>
            <li>External Consensus</li>
            <li>User Input</li>
            <li>Unavailable</li>
          </ul>
        </div>
      </CardBody>
    </Card>
  );
}

function GraphSearchAndFilters({
  filters,
  onChange,
}: {
  filters: GraphFilterState;
  onChange: (f: GraphFilterState) => void;
}) {
  const searchId = useId();
  return (
    <div className="space-y-3 rounded-md border border-[var(--border)] bg-[var(--surface)] p-3">
      <div>
        <label htmlFor={searchId} className="text-xs font-medium uppercase text-[var(--muted)]">
          Search nodes
        </label>
        <input
          id={searchId}
          type="search"
          value={filters.query}
          onChange={(e) => onChange({ ...filters, query: e.target.value })}
          placeholder="Node name, metric, risk, evidence, assumption, section…"
          className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        />
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        <Select
          label="Confidence"
          value={filters.confidence}
          onChange={(v) =>
            onChange({ ...filters, confidence: v as GraphFilterState["confidence"] })
          }
          options={[
            ["all", "All"],
            ...Object.entries(CONFIDENCE_LABELS),
          ]}
        />
        <Select
          label="Evidence strength"
          value={filters.evidenceStrength}
          onChange={(v) =>
            onChange({
              ...filters,
              evidenceStrength: v as GraphFilterState["evidenceStrength"],
            })
          }
          options={[
            ["all", "All"],
            ["has_evidence", "Has evidence"],
            ["no_evidence", "No evidence"],
          ]}
        />
        <Select
          label="Node type"
          value={filters.nodeType}
          onChange={(v) => onChange({ ...filters, nodeType: v as GraphFilterState["nodeType"] })}
          options={[
            ["all", "All"],
            ...(Object.entries(KG_NODE_TYPE_LABELS) as [string, string][]),
          ]}
        />
        <Select
          label="Research category"
          value={filters.researchCategory}
          onChange={(v) =>
            onChange({
              ...filters,
              researchCategory: v as GraphFilterState["researchCategory"],
            })
          }
          options={[
            ["all", "All (use tabs)"],
            ...(Object.entries(KG_TAB_LABELS) as [string, string][]),
          ]}
        />
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={filters.availableOnly}
            onChange={(e) => onChange({ ...filters, availableOnly: e.target.checked })}
          />
          Available only
        </label>
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={filters.hideUnknown}
            onChange={(e) => onChange({ ...filters, hideUnknown: e.target.checked })}
          />
          Hide unknown / unavailable
        </label>
      </div>
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: [string, string][] | (readonly [string, string])[];
}) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="text-xs font-medium uppercase text-[var(--muted)]">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
      >
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </div>
  );
}

const GraphCanvas = memo(function GraphCanvas({
  nodes,
  edges,
  selectedId,
  onSelect,
  tab,
}: {
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  tab: KnowledgeGraphTab;
}) {
  // Incremental / viewport: cap rendered nodes; prefer available first
  const rendered = useMemo(() => {
    const sorted = [...nodes].sort((a, b) => Number(b.available) - Number(a.available));
    return sorted.slice(0, 48);
  }, [nodes]);

  const positions = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    const cols = 4;
    rendered.forEach((n, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      map.set(n.id, { x: 8 + col * 24, y: 8 + row * 22 });
    });
    return map;
  }, [rendered]);

  const renderedIds = useMemo(() => new Set(rendered.map((n) => n.id)), [rendered]);
  const cullEdges = edges.filter((e) => renderedIds.has(e.from) && renderedIds.has(e.to)).slice(0, 80);

  return (
    <Card>
      <CardHeader
        title={`${KG_TAB_LABELS[tab]} graph`}
        description="Click a node · Arrow keys move focus in the node list below the canvas when using keyboard"
      />
      <CardBody>
        <div
          className="relative h-[28rem] overflow-auto rounded-md border border-[var(--border)] bg-[var(--surface-2)]"
          role="group"
          aria-label={`${KG_TAB_LABELS[tab]} knowledge graph canvas`}
        >
          <svg className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden>
            {cullEdges.map((e) => {
              const a = positions.get(e.from);
              const b = positions.get(e.to);
              if (!a || !b) return null;
              return (
                <line
                  key={e.id}
                  x1={`${a.x}%`}
                  y1={`${a.y}%`}
                  x2={`${b.x}%`}
                  y2={`${b.y}%`}
                  stroke="var(--border)"
                  strokeWidth="1"
                />
              );
            })}
          </svg>
          {rendered.map((n) => {
            const pos = positions.get(n.id)!;
            const active = selectedId === n.id;
            return (
              <button
                key={n.id}
                type="button"
                style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
                className={`absolute max-w-[10rem] -translate-x-1/2 -translate-y-1/2 rounded-md border px-2 py-1.5 text-left text-xs shadow-sm motion-reduce:transition-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                  CONFIDENCE_COLORS[n.confidence]
                } ${active ? "ring-2 ring-[var(--accent)]" : ""}`}
                aria-pressed={active}
                aria-label={`${n.label}, ${KG_NODE_TYPE_LABELS[n.nodeType]}, confidence ${CONFIDENCE_LABELS[n.confidence]}`}
                onClick={() => onSelect(n.id)}
              >
                <span className="block font-medium leading-tight">{n.label}</span>
                <span className="block text-[0.65rem] opacity-80">
                  {KG_NODE_TYPE_LABELS[n.nodeType]} · ev {n.evidenceCount}
                </span>
              </button>
            );
          })}
        </div>
        {nodes.length > rendered.length ? (
          <p className="mt-2 text-xs text-[var(--muted)]">
            Showing {rendered.length} of {nodes.length} nodes (viewport cull). Refine filters to focus.
          </p>
        ) : null}
      </CardBody>
    </Card>
  );
});

function GraphMiniMap({
  nodes,
  selectedId,
  onSelect,
}: {
  nodes: KnowledgeGraphNode[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const sample = nodes.slice(0, 64);
  return (
    <Card className="mt-3">
      <CardHeader title="Mini map" description="Overview navigation" />
      <CardBody>
        <div
          className="flex flex-wrap gap-1"
          role="navigation"
          aria-label="Knowledge graph mini map"
        >
          {sample.map((n) => (
            <button
              key={n.id}
              type="button"
              title={n.label}
              aria-label={n.label}
              aria-current={selectedId === n.id ? "true" : undefined}
              onClick={() => onSelect(n.id)}
              className={`h-3 w-3 rounded-sm border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                selectedId === n.id ? "border-[var(--accent)] bg-[var(--accent)]" : "border-[var(--border)] bg-[var(--surface-2)]"
              } ${n.available ? "" : "opacity-40"}`}
            />
          ))}
        </div>
      </CardBody>
    </Card>
  );
}

function GraphNodeList({
  nodes,
  edges,
  selectedId,
  onSelect,
}: {
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const onKey = (e: KeyboardEvent<HTMLUListElement>) => {
    if (!nodes.length) return;
    const idx = nodes.findIndex((n) => n.id === selectedId);
    if (e.key === "ArrowDown") {
      e.preventDefault();
      onSelect(nodes[Math.min(idx + 1, nodes.length - 1)]?.id ?? nodes[0].id);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      onSelect(nodes[Math.max(idx - 1, 0)]?.id ?? nodes[0].id);
    }
  };

  return (
    <Card>
      <CardHeader title="Nodes" description="Mobile list mode — expand a node for relationships" />
      <CardBody>
        <ul
          className="max-h-[28rem] space-y-2 overflow-y-auto"
          onKeyDown={onKey}
          aria-label="Knowledge graph nodes"
        >
          {nodes.map((n) => {
            const rel = edges.filter((e) => e.from === n.id || e.to === n.id);
            return (
              <li key={n.id}>
                <details
                  open={selectedId === n.id}
                  className="rounded-md border border-[var(--border)]"
                  onToggle={(e) => {
                    if ((e.target as HTMLDetailsElement).open) onSelect(n.id);
                  }}
                >
                  <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-2 px-3 py-2 text-sm">
                    <span className="font-medium">{n.label}</span>
                    <Badge tone={n.available ? "accent" : "neutral"}>
                      {KG_NODE_TYPE_LABELS[n.nodeType]}
                    </Badge>
                  </summary>
                  <div className="space-y-2 border-t border-[var(--border)] px-3 py-2 text-sm">
                    <ConfidenceBadge level={n.confidence} />
                    <p className="text-[var(--muted)]">{n.description}</p>
                    <p className="text-xs">Relationships ({rel.length})</p>
                    <ul className="list-disc pl-5 text-xs text-[var(--muted)]">
                      {rel.slice(0, 8).map((e) => (
                        <li key={e.id}>
                          {KG_EDGE_TYPE_LABELS[e.edgeType]}: {e.label}
                        </li>
                      ))}
                    </ul>
                  </div>
                </details>
              </li>
            );
          })}
        </ul>
      </CardBody>
    </Card>
  );
}

export function NodeDetailsPanel({ node }: { node: KnowledgeGraphNode }) {
  return (
    <Card>
      <CardHeader
        title={node.label}
        description={KG_NODE_TYPE_LABELS[node.nodeType]}
        action={<ConfidenceBadge level={node.confidence} />}
      />
      <CardBody className="space-y-2 text-sm">
        <div className="flex flex-wrap gap-2">
          <ValueCategoryBadge category={node.dataCategory} />
          <SourceBadge source={node.sourceCategory} />
          <Badge tone="neutral">Evidence {node.evidenceCount}</Badge>
        </div>
        <p>{node.description}</p>
        <p className="text-xs text-[var(--muted)]">
          Last updated: {node.lastUpdated ?? "Unavailable"}
        </p>
      </CardBody>
    </Card>
  );
}

function GraphEvidencePanel({ node }: { node: KnowledgeGraphNode }) {
  return (
    <Card>
      <CardHeader title="Evidence" />
      <CardBody>
        {node.evidence.length ? (
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {node.evidence.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-[var(--muted)]">No evidence listed for this node.</p>
        )}
        <p className="mt-2 text-xs">
          <TraceLink href="#evidence_explorer">Evidence Explorer</TraceLink>
        </p>
      </CardBody>
    </Card>
  );
}

function RelatedMetricsPanel({
  node,
  related,
  onSelect,
}: {
  node: KnowledgeGraphNode;
  related: KnowledgeGraphNode[];
  onSelect: (id: string) => void;
}) {
  return (
    <Card>
      <CardHeader title="Related metrics & nodes" />
      <CardBody className="space-y-2 text-sm">
        {node.supportingMetrics.length ? (
          <ul className="list-disc pl-5">
            {node.supportingMetrics.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        ) : (
          <p className="text-[var(--muted)]">No supporting metrics listed.</p>
        )}
        <div className="flex flex-wrap gap-2 pt-2">
          {related.slice(0, 12).map((r) => (
            <button
              key={r.id}
              type="button"
              className="min-h-11 rounded-md border border-[var(--border)] px-2 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              onClick={() => onSelect(r.id)}
            >
              {r.label}
            </button>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}

function GraphEdgePanel({
  edges,
  nodes,
  onSelect,
}: {
  edges: KnowledgeGraphEdge[];
  nodes: KnowledgeGraphNode[];
  onSelect: (id: string) => void;
}) {
  const label = (id: string) => nodes.find((n) => n.id === id)?.label ?? id;
  return (
    <Card>
      <CardHeader title="Relationships" />
      <CardBody>
        {edges.length ? (
          <ul className="space-y-2 text-sm">
            {edges.map((e) => (
              <li key={e.id} className="rounded-md border border-[var(--border)] px-2 py-2">
                <p className="text-xs text-[var(--muted)]">{KG_EDGE_TYPE_LABELS[e.edgeType]}</p>
                <p>
                  <button
                    type="button"
                    className="text-[var(--accent)] underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                    onClick={() => onSelect(e.from)}
                  >
                    {label(e.from)}
                  </button>
                  {" → "}
                  <button
                    type="button"
                    className="text-[var(--accent)] underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                    onClick={() => onSelect(e.to)}
                  >
                    {label(e.to)}
                  </button>
                </p>
                <p className="text-xs text-[var(--muted)]">{e.label}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-[var(--muted)]">No edges for this node in view.</p>
        )}
      </CardBody>
    </Card>
  );
}

function GraphTracePanels({ node }: { node: KnowledgeGraphNode }) {
  return (
    <>
      <Card>
        <CardHeader title="Decision Trace links" />
        <CardBody className="flex flex-wrap gap-2 text-sm">
          {node.decisionTraceLinks.map((href) => (
            <TraceLink key={href} href={href}>
              {href.replace("#", "")}
            </TraceLink>
          ))}
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Research sections · Reasoning Flow" />
        <CardBody className="flex flex-wrap gap-2 text-sm">
          {node.researchSectionIds.map((id) => (
            <TraceLink key={id} href={`#${id}`}>
              {id}
            </TraceLink>
          ))}
          <TraceLink href="#reasoning_flow">reasoning_flow</TraceLink>
        </CardBody>
      </Card>
    </>
  );
}

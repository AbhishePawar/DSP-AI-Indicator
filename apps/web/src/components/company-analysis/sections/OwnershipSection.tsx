"use client";

/**
 * Institutional Company Workspace — Ownership tab.
 *
 * Promoter holding, insider transactions, and institutional ownership have
 * no connected data source anywhere in the platform (no package, port, or
 * adapter) — this is an honest, wired empty state, not mocked data, matching
 * the platform-wide "Data unavailable." convention. Management-quality
 * fields that *are* covered (Capital Allocation, Governance) live under the
 * Management tab and are linked from here rather than duplicated.
 */

import { Button } from "@/components/ds";
import { useWorkspacePrefsStore } from "@/lib/company-analysis";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { SectionCard, WorkspaceEmpty } from "../WorkspacePrimitives";

export function OwnershipSection({ view }: { view: ResearchView }) {
  const setActiveSection = useWorkspacePrefsStore((s) => s.setActiveSection);

  return (
    <div className="space-y-4">
      <SectionCard
        title="Promoter Holding"
        description="No connected ownership data source — no package, port, or adapter exists in the platform yet."
      >
        <WorkspaceEmpty description="Data unavailable — no data source connected." />
      </SectionCard>
      <SectionCard
        title="Insider Transactions"
        description="No connected insider-transaction data source."
      >
        <WorkspaceEmpty description="Data unavailable — no data source connected." />
      </SectionCard>
      <SectionCard
        title="Institutional Ownership"
        description="No connected institutional-ownership data source."
      >
        <WorkspaceEmpty description="Data unavailable — no data source connected." />
      </SectionCard>
      <SectionCard
        title="Related — Management &amp; Governance"
        description={`Capital allocation and governance for ${view.company} are covered under Management — not duplicated here.`}
      >
        <Button size="sm" variant="secondary" onClick={() => setActiveSection("management")}>
          Open Management tab
        </Button>
      </SectionCard>
    </div>
  );
}

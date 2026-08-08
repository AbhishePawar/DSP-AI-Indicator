import { DocArticle } from "@/components/launch/DocArticle";
import { PageHeader } from "@/components/layout/PageHeader";

export default function ArchitectureGuidePage() {
  return (
    <div>
      <PageHeader title="Architecture Guide" description="Web 1.0.0" />
      <DocArticle
        title="DSP Platform — Architecture Guide (1.0.0)"
        sections={[
          {
            heading: "Shape",
            body: [
              "Thin Next.js client over frozen backend v1.0.0 /api/v1.",
              "Layers: Research Analysis → Knowledge Graph → Copilot (deterministic) → Reports → Portfolio presentation → Launch/Beta ops.",
            ],
          },
          {
            heading: "Hard freezes",
            body: [
              "Decision Engine, Research Engine, KG, Copilot reasoning, Portfolio calculations, Valuation, Compliance, API contracts, Research Mode, and Feature Flags are not modified in Phase C.",
            ],
          },
          {
            heading: "Further reading",
            body: [
              "See docs/ARCHITECTURE_OVERVIEW.md, docs/DSP_ARCHITECTURE_BASELINE_v1_0.md, and docs/ARCHITECTURE_GUIDE_v1.0.0.md in the repository.",
            ],
          },
        ]}
      />
    </div>
  );
}

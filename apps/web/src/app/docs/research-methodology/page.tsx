import { DocArticle } from "@/components/launch/DocArticle";
import { PageHeader } from "@/components/layout/PageHeader";

export default function ResearchMethodologyPage() {
  return (
    <div>
      <PageHeader title="Research Methodology" description="Web 1.0.0" />
      <DocArticle
        title="DSP Platform — Research Methodology (1.0.0)"
        sections={[
          {
            heading: "Principles",
            body: [
              "Every material claim should surface Evidence, Confidence, Methodology, and Limitations.",
              "Research Mode suppresses trading recommendations and target prices in the UI.",
            ],
          },
          {
            heading: "Copilot",
            body: [
              "AI Research Copilot is deterministic explainability over DSP research envelopes — not an open-ended LLM advisor.",
            ],
          },
          {
            heading: "Portfolio",
            body: [
              "Portfolio Intelligence in 1.0.0 is session-demo presentation only — no broker sync, no order routing.",
            ],
          },
        ]}
      />
    </div>
  );
}

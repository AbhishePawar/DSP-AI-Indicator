import { DocArticle } from "@/components/launch/DocArticle";
import { PageHeader } from "@/components/layout/PageHeader";

export default function UserGuidePage() {
  return (
    <div>
      <PageHeader title="User Guide" description="Web 1.0.0" />
      <DocArticle
        title="DSP Platform — User Guide (1.0.0)"
        sections={[
          {
            heading: "What DSP is",
            body: [
              "DSP AI Indicator is a research intelligence platform. It presents evidence-backed company analysis, knowledge graphs, portfolio intelligence demos, reports, and an explainability copilot.",
              "It does not execute trades, sync brokers, or provide personalized investment advice.",
            ],
          },
          {
            heading: "Getting started",
            body: [
              "Sign in → open Dashboard → run Company Analysis → explore Knowledge Graph and Copilot → optionally build a session Portfolio → export Reports.",
              "Use the floating Feedback button for bugs and UX notes. Never paste API secrets, holdings lists, or raw research envelopes into feedback.",
            ],
          },
          {
            heading: "Research Mode",
            body: [
              "Research Mode is on by default. The UI does not present BUY/SELL/HOLD labels or Target Price recommendations.",
              "Always review Evidence, Confidence, Methodology, and Limitations on analysis surfaces.",
            ],
          },
          {
            heading: "Need help?",
            body: [
              "Restart the welcome tour from Private Beta → Feedback workspace.",
              "Operators: see Administrator Guide and Launch Dashboard.",
            ],
          },
        ]}
      />
    </div>
  );
}

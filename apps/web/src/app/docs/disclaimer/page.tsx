import { DocArticle } from "@/components/launch/DocArticle";
import { PageHeader } from "@/components/layout/PageHeader";

export default function DisclaimerPage() {
  return (
    <div>
      <PageHeader title="Disclaimer" description="Web 1.0.0" />
      <DocArticle
        title="Disclaimer (1.0.0)"
        sections={[
          {
            heading: "Not investment advice",
            body: [
              "DSP outputs are research intelligence artifacts. They are not personalized investment advice, solicitations, or recommendations to buy, sell, or hold securities.",
              "Always consider Evidence, Confidence, Methodology, and Limitations. Verify with independent sources and qualified professionals where required.",
            ],
          },
          {
            heading: "Limitations",
            body: [
              "Data may be incomplete, delayed, or unavailable. Models can be wrong. Past patterns do not guarantee future outcomes.",
            ],
          },
        ]}
      />
    </div>
  );
}

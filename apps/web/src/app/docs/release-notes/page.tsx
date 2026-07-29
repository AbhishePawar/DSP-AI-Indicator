import { DocArticle } from "@/components/launch/DocArticle";
import { PageHeader } from "@/components/layout/PageHeader";

export default function ReleaseNotesDocPage() {
  return (
    <div>
      <PageHeader
        title="Release Notes"
        description="Web 2.0.0-rc · Platform 1.6.0 (P6.1 Commercial RC)"
      />
      <DocArticle
        title="Release Notes — Web 2.0.0-rc"
        sections={[
          {
            heading: "Commercial readiness",
            body: [
              "P6.1 completes packaging, pricing, support, runbooks, and release assets for commercial RC.",
              "No new analytical features. Analysis pipeline, valuation, recommendation, and AI Committee unchanged.",
            ],
          },
          {
            heading: "Highlights",
            body: [
              "Editions: Research, Professional, Enterprise with documented usage limits.",
              "In-app Quick Start, FAQ, Pricing, and Support documentation.",
              "Operational runbooks for incident, outage, backup, deploy, rollback, and security.",
            ],
          },
          {
            heading: "Decision",
            body: [
              "READY WITH MINOR CONDITIONS — controlled commercial RC; not unrestricted public GA.",
              "See docs/P6_1_COMMERCIAL_READINESS.md and docs/RELEASE_NOTES_v2.0.0-rc.md.",
            ],
          },
        ]}
      />
    </div>
  );
}

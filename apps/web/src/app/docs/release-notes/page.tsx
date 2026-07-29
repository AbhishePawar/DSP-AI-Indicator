import { DocArticle } from "@/components/launch/DocArticle";
import { PageHeader } from "@/components/layout/PageHeader";

export default function ReleaseNotesDocPage() {
  return (
    <div>
      <PageHeader
        title="Release Notes"
        description="Web 2.0.0 · Platform 2.0.0 (P8.0 GA Candidate · Release Freeze)"
      />
      <DocArticle
        title="Release Notes — Web 2.0.0"
        sections={[
          {
            heading: "General Availability candidate",
            body: [
              "P8.0 certifies the platform for GA Candidate status and activates RELEASE FREEZE.",
              "No analytical engine changes. API contract label remains v1.0.0 with frozen behaviour.",
            ],
          },
          {
            heading: "Highlights",
            body: [
              "Backend 2.0.0 · Frontend 2.0.0 · channel ga-candidate · certify_p8 gate.",
              "Architecture certification, technical debt register, and freeze policy published.",
              "Live operational conditions (paging webhooks, secrets manager, restore drills, ACME) remain.",
            ],
          },
          {
            heading: "Decision",
            body: [
              "PASS WITH CONDITIONS · GO WITH CONDITIONS — engineering freeze in effect.",
              "See docs/P8_GENERAL_AVAILABILITY.md and docs/RELEASE_FREEZE.md.",
            ],
          },
        ]}
      />
    </div>
  );
}

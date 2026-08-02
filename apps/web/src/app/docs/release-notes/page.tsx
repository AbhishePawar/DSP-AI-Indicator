import { DocArticle } from "@/components/launch/DocArticle";
import { PageHeader } from "@/components/layout/PageHeader";

export default function ReleaseNotesDocPage() {
  return (
    <div>
      <PageHeader
        title="Release Notes"
        description="Web 2.0.0-rc.1 · Platform 2.0.0 (EPS-003 Version 2.0 Release Candidate)"
      />
      <DocArticle
        title="Release Notes — Web 2.0.0-rc.1"
        sections={[
          {
            heading: "Version 2.0 Release Candidate",
            body: [
              "EPS-003 hardens the platform as a production-grade Release Candidate under feature freeze.",
              "No analytical engine changes. API contract label remains v1.0.0 with frozen behaviour.",
              "Commercial GA is not approved — see docs/releases/RC4_RELEASE_CANDIDATE_REPORT.md.",
            ],
          },
          {
            heading: "Highlights",
            body: [
              "Product 2.0.0-rc.1 · Frontend 2.0.0-rc.1 · Backend dsp_platform@2.0.0 · channel rc.",
              "Enterprise foundation (EPS-002) included with Null billing / in-memory store caveats.",
              "RC artefacts under docs/releases/ (RC4 report, limitations, checklist, freeze, debt, roadmap).",
            ],
          },
          {
            heading: "Decision",
            body: [
              "RELEASE CANDIDATE — suitable for independent audit and deployment planning.",
              "Not Commercial GA. See docs/releases/RELEASE_NOTES_v2.0_RC.md.",
            ],
          },
        ]}
      />
    </div>
  );
}

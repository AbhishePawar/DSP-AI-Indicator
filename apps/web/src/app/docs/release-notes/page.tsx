import { DocArticle } from "@/components/launch/DocArticle";
import { PageHeader } from "@/components/layout/PageHeader";

export default function ReleaseNotesDocPage() {
  return (
    <div>
      <PageHeader title="Release Notes" description="Web 1.0.0" />
      <DocArticle
        title="Release Notes — Web 1.0.0"
        sections={[
          {
            heading: "Promotion",
            body: [
              "Promotes Release Candidate 0.9.5 to the first stable public web release.",
              "No new product features. Validation, freeze, monitoring, documentation, and launch ops only.",
            ],
          },
          {
            heading: "Highlights",
            body: [
              "Launch Dashboard with quality gates (critical=0, regression/a11y/perf/security PASS).",
              "CSP enforced; production source maps disabled; version manifest frozen.",
              "User, Administrator, Architecture, Methodology guides + Privacy, Terms, Disclaimer.",
            ],
          },
        ]}
      />
    </div>
  );
}

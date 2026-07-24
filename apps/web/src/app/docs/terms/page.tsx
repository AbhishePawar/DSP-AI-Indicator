import { DocArticle } from "@/components/launch/DocArticle";
import { PageHeader } from "@/components/layout/PageHeader";

export default function TermsPage() {
  return (
    <div>
      <PageHeader title="Terms of Use" description="Web 1.0.0" />
      <DocArticle
        title="Terms of Use (1.0.0)"
        sections={[
          {
            heading: "Acceptable use",
            body: [
              "Use DSP for research intelligence and education within your organization's authorization.",
              "Do not attempt to bypass authentication, scrape undisclosed APIs, or reverse-engineer restricted components.",
            ],
          },
          {
            heading: "No brokerage",
            body: [
              "DSP does not provide brokerage, order execution, or custody. Portfolio tools are demonstrative unless separately contracted.",
            ],
          },
        ]}
      />
    </div>
  );
}

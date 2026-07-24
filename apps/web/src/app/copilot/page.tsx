import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Card, CardBody } from "@/components/ui/Card";

export default function CopilotPage() {
  return (
    <div>
      <PageHeader
        title="AI Research Copilot"
        description="Explainability assistant for DSP Research — not an independent recommendation engine."
      />
      <Card>
        <CardBody className="space-y-4">
          <Alert tone="info" title="Open from Company Analysis">
            The Copilot lives as a session panel on the analysis workspace. It
            explains Decision Trace, Evidence, Confidence, Assumptions, and the
            Knowledge Graph without fabricating numbers or Buy/Sell advice.
          </Alert>
          <Link
            href="/analysis"
            className="inline-flex min-h-11 items-center justify-center rounded-md bg-[var(--accent)] px-4 text-sm font-medium text-[var(--accent-fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            Open Analysis Workspace
          </Link>
        </CardBody>
      </Card>
    </div>
  );
}

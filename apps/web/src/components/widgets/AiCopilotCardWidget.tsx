"use client";

import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";

export function AiCopilotCardWidget() {
  return (
    <Card>
      <CardHeader
        title="AI Research Copilot"
        description="Explains DSP Research in the analysis workspace"
      />
      <CardBody className="space-y-3">
        <p className="text-sm text-[var(--muted)]">
          Session-only explainability assistant — no Buy/Sell advice, no invented
          numbers. Open analysis and use Ask Research Copilot.
        </p>
        <Link href="/analysis">
          <Button>Open Analysis Copilot</Button>
        </Link>
      </CardBody>
    </Card>
  );
}

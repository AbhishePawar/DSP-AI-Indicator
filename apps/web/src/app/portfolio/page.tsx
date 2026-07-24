"use client";

import { useMemo, useState } from "react";

import { PortfolioWorkspace } from "@/components/portfolio/PortfolioWorkspace";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import {
  buildDemoPortfolio,
  emptyPortfolioWorkspace,
} from "@/lib/portfolio/portfolioWorkspace";

export default function PortfolioPage() {
  const [mode, setMode] = useState<"demo" | "empty">("demo");
  const view = useMemo(
    () => (mode === "demo" ? buildDemoPortfolio() : emptyPortfolioWorkspace()),
    [mode],
  );

  return (
    <div>
      <PageHeader
        title="Portfolio Intelligence"
        description="Presentation layer above company analysis and below Reports — aggregates session holdings with explicit Unavailable states. No broker sync. No automatic trading."
      />
      <Alert tone="info" title="Sprint 8 · Research Mode">
        Portfolio metrics show confidence, evidence, methodology, and timestamps.
        Decision Engine, Analysis API, Knowledge Graph, and Copilot are unchanged.
      </Alert>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          variant={mode === "demo" ? "primary" : "secondary"}
          onClick={() => setMode("demo")}
        >
          Load demo session
        </Button>
        <Button
          variant={mode === "empty" ? "primary" : "secondary"}
          onClick={() => setMode("empty")}
        >
          Empty portfolio
        </Button>
      </div>
      <div className="mt-6">
        <PortfolioWorkspace view={view} />
      </div>
    </div>
  );
}

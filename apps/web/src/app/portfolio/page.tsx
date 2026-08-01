"use client";

/**
 * P9.5 / EPIC-006 — Portfolio Intelligence Workspace route.
 */

import { Suspense } from "react";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { PortfolioIntelligenceWorkspace } from "@/components/portfolio-intelligence";
import { WorkspaceSkeleton } from "@/components/portfolio-intelligence/Primitives";
import { PageHeader } from "@/components/layout/PageHeader";

export default function PortfolioPage() {
  return (
    <ProtectedRoute>
      <div className="space-y-4">
        <PageHeader
          title="Portfolio Intelligence Workspace"
          description="Institutional portfolio health, allocation, quality, valuation, risk, and explainability over session holdings and /api/v1/portfolio/intelligence. No client-side scoring — missing feeds stay Data unavailable."
        />
        <Suspense fallback={<WorkspaceSkeleton />}>
          <PortfolioIntelligenceWorkspace />
        </Suspense>
      </div>
    </ProtectedRoute>
  );
}

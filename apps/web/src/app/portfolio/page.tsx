"use client";

/**
 * P9.5 / EPIC-006 — Portfolio Intelligence Workspace route.
 * RC3-004 — dynamic import for workspace code-splitting.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { WorkspaceSkeleton } from "@/components/portfolio-intelligence/Primitives";
import { PageHeader } from "@/components/layout/PageHeader";

const PortfolioIntelligenceWorkspace = dynamic(
  () =>
    import("@/components/portfolio-intelligence").then((m) => ({
      default: m.PortfolioIntelligenceWorkspace,
    })),
  {
    ssr: false,
    loading: () => <WorkspaceSkeleton />,
  },
);

export default function PortfolioPage() {
  return (
    <ProtectedRoute>
      <div className="space-y-4">
        <PageHeader
          title="Portfolio Intelligence Workspace"
          description="Institutional portfolio coverage, allocation, quality, valuation, risk, and explainability over session holdings and /api/v1/portfolio/intelligence. No client-side scoring — missing feeds stay Data unavailable."
        />
        <Suspense fallback={<WorkspaceSkeleton />}>
          <PortfolioIntelligenceWorkspace />
        </Suspense>
      </div>
    </ProtectedRoute>
  );
}

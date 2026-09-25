"use client";

/**
 * Portfolio — Figma Make `Portfolio.tsx` (summary cards · Holdings · Sector
 * Allocation) over the session portfolio store and /api/v1/market/quote.
 * No client-side scoring — quantity-dependent figures stay Data unavailable.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Skeleton } from "@/components/ds";

function PortfolioFallback() {
  return (
    <div className="space-y-4 py-6" role="status" aria-live="polite" aria-label="Loading portfolio">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

const PortfolioHoldings = dynamic(
  () => import("@/components/pages").then((m) => ({ default: m.PortfolioHoldings })),
  { ssr: false, loading: () => <PortfolioFallback /> },
);

export default function PortfolioPage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={<PortfolioFallback />}>
        <PortfolioHoldings />
      </Suspense>
    </ProtectedRoute>
  );
}

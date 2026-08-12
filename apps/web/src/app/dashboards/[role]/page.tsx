"use client";

import { Suspense } from "react";
import { useParams, useSearchParams } from "next/navigation";

import { RoleDashboard } from "@/components/dashboards";
import { WidgetLoading } from "@/components/dashboard/DashboardWidgetShell";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  isEnterpriseDashboardRole,
  type EnterpriseDashboardRole,
} from "@/lib/dashboards/roleRegistry";

function RoleDashboardInner() {
  const params = useParams<{ role: string }>();
  const search = useSearchParams();
  const role = params?.role ?? "";

  if (!isEnterpriseDashboardRole(role)) {
    return (
      <div className="p-6">
        <PageHeader
          title="Dashboard not found"
          description="Unknown enterprise dashboard role."
        />
      </div>
    );
  }

  return (
    <RoleDashboard
      role={role as EnterpriseDashboardRole}
      portfolioId={search.get("portfolio_id") ?? undefined}
      symbols={search.get("symbols") ?? undefined}
      watchlistId={search.get("watchlist_id") ?? undefined}
      clientPortfolioIds={search.get("client_portfolio_ids") ?? undefined}
      workflowId={search.get("workflow_id") ?? undefined}
    />
  );
}

export default function EnterpriseRoleDashboardPage() {
  return (
    <Suspense fallback={<div className="p-6"><WidgetLoading label="Loading dashboard" /></div>}>
      <RoleDashboardInner />
    </Suspense>
  );
}

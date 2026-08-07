"use client";

/**
 * RC1 Milestone 6 — role-specific enterprise dashboard shell.
 * Lazy-loads section cards; reuses DashboardWidgetShell. Thin /api/v1 client only.
 */

import { Suspense, lazy, useMemo } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { Alert, Button } from "@/components/ds";
import { PageHeader } from "@/components/layout/PageHeader";
import { WidgetLoading } from "@/components/dashboard/DashboardWidgetShell";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  ENTERPRISE_DASHBOARD_ROLES,
  metaForRole,
  type EnterpriseDashboardRole,
} from "@/lib/dashboards/roleRegistry";
import { featureFlags } from "@/lib/featureFlags";
import { SurfaceTrustChrome } from "@/components/trust/SurfaceTrustChrome";
import { dashboardSurfaceTrust } from "@/lib/trust/surfaceTrust";

const LazySectionCard = lazy(() =>
  import("./DashboardSectionCard").then((m) => ({
    default: m.DashboardSectionCard,
  })),
);

export function RoleDashboard({
  role,
  portfolioId,
  symbols,
  watchlistId,
  clientPortfolioIds,
  workflowId,
}: {
  role: EnterpriseDashboardRole;
  portfolioId?: string;
  symbols?: string;
  watchlistId?: string;
  clientPortfolioIds?: string;
  workflowId?: string;
}) {
  const { session } = useAuth();
  const meta = metaForRole(role);

  const query = useQuery({
    queryKey: [
      "enterprise-dashboard",
      role,
      portfolioId,
      symbols,
      watchlistId,
      clientPortfolioIds,
      workflowId,
    ],
    queryFn: () =>
      api.enterpriseDashboard(
        role,
        {
          portfolio_id: portfolioId,
          symbols,
          watchlist_id: watchlistId,
          client_portfolio_ids: clientPortfolioIds,
          workflow_id: workflowId,
        },
        { token: session?.accessToken },
      ),
    enabled: featureFlags.enterpriseDashboards,
    retry: false,
  });

  const widgetKeys = useMemo(
    () => meta?.widgetKeys ?? [],
    [meta?.widgetKeys],
  );

  if (!featureFlags.enterpriseDashboards) {
    return (
      <div className="space-y-4 p-6">
        <Alert variant="warning" title="Enterprise dashboards disabled.">
          Set NEXT_PUBLIC_ENTERPRISE_DASHBOARDS=true to enable role dashboards.
        </Alert>
      </div>
    );
  }

  const trustSummary = useMemo(
    () =>
      dashboardSurfaceTrust({
        widgetCount: widgetKeys.length,
        note: `Enterprise role dashboard · ${role} · aggregation only`,
      }),
    [role, widgetKeys.length],
  );

  return (
    <div className="space-y-6 p-4 md:p-6" data-testid={`role-dashboard-${role}`}>
      <SurfaceTrustChrome summary={trustSummary} />
      <PageHeader
        title={meta?.title ?? "Enterprise Dashboard"}
        description={meta?.description}
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/dashboard">
              <Button size="sm" variant="secondary">
                Home dashboard
              </Button>
            </Link>
            {ENTERPRISE_DASHBOARD_ROLES.filter((r) => r.role !== role).map(
              (r) => (
                <Link key={r.role} href={r.href}>
                  <Button size="sm" variant="secondary">
                    {r.title.replace(" Dashboard", "")}
                  </Button>
                </Link>
              ),
            )}
          </div>
        }
      />

      {query.isError ? (
        <Alert variant="error" title="Data unavailable.">
          {(query.error as Error)?.message ||
            "Unable to load enterprise dashboard."}
        </Alert>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {widgetKeys.map((key) => {
          const section = query.data?.result?.widgets?.[key];
          return (
            <Suspense key={key} fallback={<WidgetLoading label={`Loading ${key}`} />}>
              <LazySectionCard
                sectionKey={key}
                section={
                  query.isLoading
                    ? undefined
                    : (section as
                        | import("@/lib/api/client").DashboardWidgetSection
                        | undefined)
                }
              />
            </Suspense>
          );
        })}
      </div>

      {query.data?.result?.generated_at ? (
        <p className="text-xs text-[var(--muted)]">
          Generated at {query.data.result.generated_at} · aggregation only · no
          browser calculations
        </p>
      ) : null}
    </div>
  );
}

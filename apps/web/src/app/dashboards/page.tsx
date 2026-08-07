"use client";

import Link from "next/link";

import { Button, Card, CardContent, CardHeader, CardTitle } from "@/components/ds";
import { PageHeader } from "@/components/layout/PageHeader";
import { ENTERPRISE_DASHBOARD_ROLES } from "@/lib/dashboards/roleRegistry";
import { featureFlags } from "@/lib/featureFlags";

export default function EnterpriseDashboardsIndexPage() {
  if (!featureFlags.enterpriseDashboards) {
    return (
      <div className="p-6">
        <PageHeader title="Enterprise Dashboards" description="Feature disabled." />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 md:p-6" data-testid="enterprise-dashboards-index">
      <PageHeader
        title="Enterprise Dashboards"
        description="Role-specific views over frozen /api/v1 engines — no duplicated calculations."
        actions={
          <Link href="/dashboard">
            <Button size="sm" variant="secondary">
              Home dashboard
            </Button>
          </Link>
        }
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {ENTERPRISE_DASHBOARD_ROLES.map((role) => (
          <Card key={role.role}>
            <CardHeader>
              <CardTitle className="text-base">{role.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-[var(--muted)]">{role.description}</p>
              <Link href={role.href}>
                <Button size="sm">Open</Button>
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

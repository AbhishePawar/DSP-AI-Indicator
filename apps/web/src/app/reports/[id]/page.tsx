"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Card, CardBody } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";

export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const reportId = decodeURIComponent(params.id);
  const { session } = useAuth();

  const report = useQuery({
    queryKey: ["report", reportId],
    queryFn: () => api.getReport(reportId, { token: session?.accessToken }),
    enabled: Boolean(reportId && session?.accessToken),
    retry: false,
  });

  return (
    <div>
      <PageHeader
        title="Report"
        description={`GET /api/v1/report/${reportId}`}
      />
      <Card>
        <CardBody>
          {report.isLoading ? <Spinner label="Loading report…" /> : null}
          {report.isError ? (
            <ErrorState
              title="Report unavailable"
              description={(report.error as Error).message}
            />
          ) : null}
          {report.data ? (
            <div className="space-y-4">
              <Alert tone="info" title="Thin client">
                Displaying the API response only. No valuation or recommendation
                is derived in the browser.
              </Alert>
              <pre className="overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--bg)] p-4 text-xs text-[var(--muted)]">
                {JSON.stringify(report.data, null, 2)}
              </pre>
            </div>
          ) : null}
        </CardBody>
      </Card>
    </div>
  );
}

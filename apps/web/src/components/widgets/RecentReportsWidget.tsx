"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQueries } from "@tanstack/react-query";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { Table, Td, Tr } from "@/components/ui/Table";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  listRecentReports,
  type RecentReportEntry,
} from "@/lib/recentReports";

export function RecentReportsWidget() {
  const { session } = useAuth();
  const [entries, setEntries] = useState<RecentReportEntry[]>([]);

  useEffect(() => {
    setEntries(listRecentReports());
  }, []);

  const queries = useQueries({
    queries: entries.slice(0, 5).map((entry) => ({
      queryKey: ["report", entry.reportId],
      queryFn: () =>
        api.getReport(entry.reportId, { token: session?.accessToken }),
      enabled: Boolean(session?.accessToken) && entries.length > 0,
      retry: false,
    })),
  });

  return (
    <Card className="sm:col-span-2 xl:col-span-2">
      <CardHeader
        title="Recent Reports"
        description="GET /api/v1/report/{id} for locally remembered ids"
        action={
          <Link
            href="/research/institutional"
            className="text-xs text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            Research Reports
          </Link>
        }
      />
      <CardBody className="pt-2">
        {entries.length === 0 ? (
          <EmptyState
            title="No recent reports"
            description="Analyze a company to store a report id locally. The browser never computes valuation."
            actionLabel="Analyze Company"
            onAction={() => {
              window.location.href = "/analysis";
            }}
          />
        ) : (
          <Table headers={["Report ID", "Symbol", "API status"]} caption="Recent reports">
            {entries.slice(0, 5).map((entry, i) => {
              const q = queries[i];
              return (
                <Tr key={entry.reportId}>
                  <Td>
                    <Link
                      href={
                        entry.symbol
                          ? `/research/institutional?symbol=${encodeURIComponent(entry.symbol)}`
                          : "/research/institutional"
                      }
                      className="text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                    >
                      {entry.reportId}
                    </Link>
                  </Td>
                  <Td>{entry.symbol ?? "—"}</Td>
                  <Td>
                    {q?.isLoading ? (
                      <Skeleton className="h-4 w-16" />
                    ) : q?.isError ? (
                      <span className="text-[var(--danger-fg)]">unavailable</span>
                    ) : q?.data ? (
                      <span className="text-[var(--muted)]">{q.data.format}</span>
                    ) : (
                      "—"
                    )}
                  </Td>
                </Tr>
              );
            })}
          </Table>
        )}
      </CardBody>
    </Card>
  );
}

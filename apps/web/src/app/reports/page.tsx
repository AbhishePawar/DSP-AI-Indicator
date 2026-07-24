"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Table, Td, Tr } from "@/components/ui/Table";
import {
  listRecentReports,
  type RecentReportEntry,
} from "@/lib/recentReports";

export default function ReportsPage() {
  const [entries, setEntries] = useState<RecentReportEntry[]>([]);

  useEffect(() => {
    setEntries(listRecentReports());
  }, []);

  return (
    <div>
      <PageHeader
        title="Reports"
        description="Recent report ids remembered in this browser. Payloads load via GET /api/v1/report/{id}."
      />
      <Card>
        <CardBody>
          {entries.length === 0 ? (
            <EmptyState
              title="No reports yet"
              description="Run Company Analysis to receive a report_id from the API."
              actionLabel="Analyze Company"
              onAction={() => {
                window.location.href = "/analysis";
              }}
            />
          ) : (
            <Table
              headers={["Report ID", "Symbol", "Saved"]}
              caption="Locally remembered reports"
            >
              {entries.map((entry) => (
                <Tr key={entry.reportId}>
                  <Td>
                    <Link
                      href={`/reports/${encodeURIComponent(entry.reportId)}`}
                      className="text-[var(--accent)] hover:underline"
                    >
                      {entry.reportId}
                    </Link>
                  </Td>
                  <Td>{entry.symbol ?? "—"}</Td>
                  <Td>
                    <time dateTime={entry.savedAt}>
                      {new Date(entry.savedAt).toLocaleString()}
                    </time>
                  </Td>
                </Tr>
              ))}
            </Table>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

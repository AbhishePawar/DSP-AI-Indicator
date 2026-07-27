"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "@/components/layout/PageHeader";
import { WidgetGrid } from "@/components/layout/ContentArea";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { api } from "@/lib/api/client";
import { env } from "@/lib/env";
import { useAuth } from "@/lib/auth/AuthProvider";

export default function DashboardPage() {
  const { session } = useAuth();
  const token = session?.accessToken;

  const healthQuery = useQuery({
    queryKey: ["terminal", "health"],
    queryFn: () => api.health({ token }),
    retry: 1,
    staleTime: 30_000,
  });

  const versionQuery = useQuery({
    queryKey: ["terminal", "version"],
    queryFn: () => api.version({ token }),
    retry: 1,
    staleTime: 60_000,
  });

  const ready = healthQuery.data?.ready;
  const pv = versionQuery.data?.platform_version ?? "—";
  const pipeline = versionQuery.data?.pipeline_version ?? "—";

  return (
    <div>
      <PageHeader
        title="Investment Terminal"
        description="Platform health, analysis summary, and quick actions."
      />

      {/* Platform status strip */}
      <section aria-label="Platform status">
        <WidgetGrid>
          <Card>
            <CardHeader title="Platform Version" />
            <CardBody className="font-mono text-sm">
              <Row label="Frontend" value={`v${env.frontendVersion}`} />
              <Row label="Platform" value={pv} />
              <Row label="Pipeline" value={pipeline} />
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="API Status" />
            <CardBody>
              <div className="flex items-center gap-2">
                <span
                  className={`terminal-dot${ready === false ? " terminal-dot--danger" : ready === undefined ? " terminal-dot--warn" : ""}`}
                  aria-hidden
                />
                <span className="text-sm font-medium">
                  {ready === undefined
                    ? "Checking…"
                    : ready
                      ? "Connected"
                      : "Unavailable"}
                </span>
                <Badge
                  tone={ready ? "success" : ready === false ? "danger" : "neutral"}
                >
                  {healthQuery.data?.status ?? "—"}
                </Badge>
              </div>
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Environment" />
            <CardBody className="font-mono text-sm">
              <Row label="Mode" value={env.environment} />
              <Row label="API" value={env.apiBaseUrl} />
            </CardBody>
          </Card>
        </WidgetGrid>
      </section>

      {/* Analysis summary */}
      <section aria-label="Analysis summary" className="mt-6">
        <Card>
          <CardHeader
            title="Analysis Summary"
            description="Placeholder — analysis metrics from session"
          />
          <CardBody>
            <div className="grid gap-4 sm:grid-cols-4">
              <Metric label="Total Analyses" value="—" />
              <Metric label="Latest Company" value="—" />
              <Metric label="Average Runtime" value="—" />
              <Metric label="Pipeline Status" value={ready ? "Online" : "—"} />
            </div>
          </CardBody>
        </Card>
      </section>

      {/* Quick actions */}
      <section aria-label="Quick actions" className="mt-6">
        <Card>
          <CardHeader title="Quick Actions" />
          <CardBody className="flex flex-wrap gap-3">
            <Link href="/analysis">
              <Button>Analyse Company</Button>
            </Link>
            <Link href="/documentation">
              <Button variant="secondary">Open Documentation</Button>
            </Link>
            <Link href="/research">
              <Button variant="secondary">Research Workspace</Button>
            </Link>
          </CardBody>
        </Card>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-[var(--muted)]">{label}</p>
      <p className="mt-1 font-[family-name:var(--font-display)] text-xl tracking-tight">
        {value}
      </p>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-[var(--muted)]">{label}</span>
      <span>{value}</span>
    </div>
  );
}

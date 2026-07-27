"use client";

import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { env } from "@/lib/env";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";

export default function DocumentationPage() {
  const { session } = useAuth();
  const versionQuery = useQuery({
    queryKey: ["terminal", "version"],
    queryFn: () => api.version({ token: session?.accessToken }),
    retry: 1,
    staleTime: 60_000,
  });

  return (
    <div>
      <PageHeader
        title="Documentation"
        description="Platform documentation, architecture, and release information."
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader title="Project Version" />
          <CardBody className="space-y-2 font-mono text-sm">
            <Row label="Frontend" value={`v${env.frontendVersion}`} />
            <Row
              label="API package"
              value={versionQuery.data?.api_package_version ?? "—"}
            />
            <Row
              label="Platform"
              value={versionQuery.data?.platform_version ?? "—"}
            />
            <Row
              label="Pipeline"
              value={versionQuery.data?.pipeline_version ?? "—"}
            />
            <Row
              label="Docs suite"
              value={versionQuery.data?.docs_version ?? "—"}
            />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Architecture" />
          <CardBody className="text-sm text-[var(--muted)]">
            <p>
              Next.js 15 + React 19 + TanStack Query thin client over
              /api/v1. Backend: Python FastAPI + dsp_platform orchestration.
            </p>
            <p className="mt-2">
              Frontend imports ONLY HTTP responses — no backend packages.
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Technology Stack" />
          <CardBody>
            <ul className="list-inside list-disc text-sm text-[var(--muted)]">
              <li>Next.js 15 (App Router)</li>
              <li>React 19</li>
              <li>TypeScript 5</li>
              <li>TanStack Query v5</li>
              <li>Tailwind CSS v4</li>
              <li>Vitest</li>
            </ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Release Notes" />
          <CardBody className="text-sm text-[var(--muted)]">
            <p>
              <strong>EPIC-004A</strong> — Investment Terminal Foundation.
              Application shell, terminal navigation, status bar, dark theme.
            </p>
            <p className="mt-2">
              Prior: EPIC-003 Intelligence Workspace · EPIC-002 API · EPIC-001 Composition.
            </p>
          </CardBody>
        </Card>
      </div>
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

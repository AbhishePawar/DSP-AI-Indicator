"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";

export function PlatformHealthWidget() {
  const { session } = useAuth();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health({ token: session?.accessToken }),
  });

  return (
    <Card>
      <CardHeader
        title="Platform Health"
        description="GET /api/v1/health"
        action={
          <Link
            href="/dashboard"
            className="text-xs text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            Details
          </Link>
        }
      />
      <CardBody>
        {health.isLoading ? (
          <div className="space-y-2" aria-busy="true">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : null}
        {health.isError ? (
          <ErrorState
            title="Health check failed"
            description={(health.error as Error).message}
          />
        ) : null}
        {health.data ? (
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={health.data.ready ? "success" : "warning"}>
                {health.data.status}
              </Badge>
              <span className="text-[var(--muted)]">
                ready={String(health.data.ready)}
              </span>
            </div>
            <p className="text-[var(--muted)]">
              API {health.data.api_version} · platform{" "}
              {health.data.platform_version ?? "n/a"}
            </p>
          </div>
        ) : null}
      </CardBody>
    </Card>
  );
}

"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";

export function PlatformInfoWidget() {
  const { session } = useAuth();
  const platform = useQuery({
    queryKey: ["platform"],
    queryFn: () => api.platform({ token: session?.accessToken }),
  });

  return (
    <Card>
      <CardHeader
        title="Platform Information"
        description="GET /api/v1/platform"
        action={
          <Link
            href="/platform"
            className="text-xs text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            Details
          </Link>
        }
      />
      <CardBody>
        {platform.isLoading ? (
          <div className="space-y-2" aria-busy="true">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ) : null}
        {platform.isError ? (
          <ErrorState
            title="Platform info unavailable"
            description={(platform.error as Error).message}
          />
        ) : null}
        {platform.data ? (
          <div className="space-y-2 text-sm">
            <p className="font-medium">
              {platform.data.name}{" "}
              <span className="text-[var(--muted)]">v{platform.data.version}</span>
            </p>
            <div className="flex flex-wrap gap-1.5">
              <Badge tone="accent">{platform.data.status}</Badge>
              <Badge>{platform.data.environment}</Badge>
            </div>
            <p className="text-[var(--muted)]">
              {platform.data.capabilities.length} capabilities ·{" "}
              {platform.data.registered_services.length} services
            </p>
          </div>
        ) : null}
      </CardBody>
    </Card>
  );
}

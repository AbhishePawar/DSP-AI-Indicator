"use client";

import { Suspense, lazy } from "react";

import { Skeleton } from "@/components/ds";
import { PageHeader } from "@/components/layout/PageHeader";

const SaasPlatform = lazy(() =>
  import("@/components/saas-platform").then((m) => ({
    default: m.SaasPlatform,
  })),
);

export default function SaasPlatformPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-4 p-6">
          <PageHeader
            title="Commercial SaaS Platform"
            description="Loading…"
          />
          <Skeleton className="h-40 w-full" />
        </div>
      }
    >
      <SaasPlatform />
    </Suspense>
  );
}

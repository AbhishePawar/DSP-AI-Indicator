"use client";

import { Suspense, lazy } from "react";

import { Skeleton } from "@/components/ds";
import { PageHeader } from "@/components/layout/PageHeader";

const ControlCenter = lazy(() =>
  import("@/components/control-center").then((m) => ({
    default: m.ControlCenter,
  })),
);

export default function ControlCenterPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-4 p-6">
          <PageHeader
            title="Super Admin Control Center"
            description="Loading…"
          />
          <Skeleton className="h-40 w-full" />
        </div>
      }
    >
      <ControlCenter />
    </Suspense>
  );
}

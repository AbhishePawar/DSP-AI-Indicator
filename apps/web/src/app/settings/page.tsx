"use client";

/**
 * EPIC-F009 — Settings & User Preferences landing page.
 * RC3-004 — dynamic import for workspace code-splitting.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { WorkspaceSkeleton } from "@/components/settings-workspace/Primitives";
import { PageHeader } from "@/components/layout/PageHeader";

const SettingsWorkspace = dynamic(
  () =>
    import("@/components/settings-workspace").then((m) => ({
      default: m.SettingsWorkspace,
    })),
  {
    ssr: false,
    loading: () => <WorkspaceSkeleton />,
  },
);

export default function SettingsPage() {
  return (
    <div className="space-y-4">
      <PageHeader
        title="Settings & Preferences"
        description="Manage UI preferences locally and view account information from existing auth APIs. No new backend behaviour."
      />
      <Suspense fallback={<WorkspaceSkeleton />}>
        <SettingsWorkspace />
      </Suspense>
    </div>
  );
}

import { Suspense } from "react";

import { InstitutionalReportsWorkspace } from "@/components/institutional-reports";

export default function InstitutionalResearchReportsPage() {
  return (
    <Suspense
      fallback={
        <div
          className="p-4 text-sm text-[var(--muted)]"
          role="status"
          aria-live="polite"
        >
          Loading institutional research reports workspace…
        </div>
      }
    >
      <InstitutionalReportsWorkspace />
    </Suspense>
  );
}

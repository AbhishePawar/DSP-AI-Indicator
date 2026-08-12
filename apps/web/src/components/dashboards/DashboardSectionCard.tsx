"use client";

import type { ReactNode } from "react";

import type { DashboardWidgetSection } from "@/lib/api/client";
import {
  DashboardWidgetShell,
  WidgetUnavailable,
} from "@/components/dashboard/DashboardWidgetShell";

function titleFromKey(key: string): string {
  return key
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function DashboardSectionCard({
  sectionKey,
  section,
  action,
}: {
  sectionKey: string;
  section?: DashboardWidgetSection | null;
  action?: ReactNode;
}) {
  const title = titleFromKey(sectionKey);
  if (!section || section.available !== true) {
    return (
      <DashboardWidgetShell title={title} description={section?.source}>
        <WidgetUnavailable
          description={section?.message || "Data unavailable."}
        />
      </DashboardWidgetShell>
    );
  }

  return (
    <DashboardWidgetShell
      title={title}
      description={section.source}
      action={action}
    >
      <pre
        className="max-h-64 overflow-auto whitespace-pre-wrap break-words text-xs text-[var(--foreground)]"
        data-testid={`dashboard-section-${sectionKey}`}
      >
        {JSON.stringify(section.data, null, 2)}
      </pre>
    </DashboardWidgetShell>
  );
}

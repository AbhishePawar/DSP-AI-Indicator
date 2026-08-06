"use client";

/**
 * RC1 Milestone 5 — Workflow Automation route.
 * Alert Rules, Scheduled Reports, Notification Center.
 */

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { PageHeader } from "@/components/layout/PageHeader";
import { WorkflowAutomationWorkspace } from "@/components/workflow-automation/WorkflowAutomationWorkspace";

export default function WorkflowAutomationPage() {
  return (
    <ProtectedRoute>
      <div className="space-y-4">
        <PageHeader
          title="Workflow Automation"
          description="Price, valuation, and research-refresh alerts; scheduled report definitions; and your Notification Center. Every evaluation reuses existing engines — never fabricated."
        />
        <WorkflowAutomationWorkspace />
      </div>
    </ProtectedRoute>
  );
}

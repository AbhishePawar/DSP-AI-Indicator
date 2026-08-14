"use client";

/**
 * Workflow Automation Workspace (RC1 Milestone 5) — Alert Rules, Scheduled
 * Reports, Notification Center. Orchestration-only presentation layer;
 * every evaluated/scheduled value is server-computed by
 * dsp_platform.workflow_automation, reusing Portfolio Analytics/
 * Intelligence Engine and the Data Connector Framework — no new engine.
 */

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";
import { usePersistence } from "@/providers/PersistenceProvider";
import { AlertRulesPanel } from "./AlertRulesPanel";
import { NotificationCenterPanel } from "./NotificationCenterPanel";
import { ScheduledReportsPanel } from "./ScheduledReportsPanel";

export function WorkflowAutomationWorkspace() {
  const { session } = useAuth();
  const token = session?.accessToken ?? null;
  const { serverPortfolioId } = usePersistence();

  return (
    <div className="space-y-4">
      <Tabs defaultValue="alerts">
        <TabsList aria-label="Workflow Automation sections">
          <TabsTrigger value="alerts">Alert Rules</TabsTrigger>
          <TabsTrigger value="schedules">Scheduled Reports</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
        </TabsList>
        <TabsContent value="alerts">
          <AlertRulesPanel token={token} defaultPortfolioId={serverPortfolioId} />
        </TabsContent>
        <TabsContent value="schedules">
          <ScheduledReportsPanel token={token} defaultPortfolioId={serverPortfolioId} />
        </TabsContent>
        <TabsContent value="notifications">
          <NotificationCenterPanel token={token} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

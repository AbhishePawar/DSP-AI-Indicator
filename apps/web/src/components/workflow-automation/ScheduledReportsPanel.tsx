"use client";

/**
 * Scheduled Reports panel (RC1 Milestone 5) — presentation + form only.
 * "Run now" is the only implemented execution path — no autonomous
 * scheduler exists at this boundary (see docs/WORKFLOW_AUTOMATION_GUIDE.md).
 */

import { useState } from "react";

import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Skeleton,
} from "@/components/ds";
import { mapScheduledReportViews } from "@/lib/workflow-automation/mapWorkflowAutomation";
import { useScheduledReports } from "@/lib/workflow-automation/useWorkflowAutomation";

export function ScheduledReportsPanel({
  token,
  defaultPortfolioId,
}: {
  token: string | null | undefined;
  defaultPortfolioId?: string | null;
}) {
  const { schedules, isLoading, createSchedule, deleteSchedule, runNow } =
    useScheduledReports(token);
  const [frequency, setFrequency] = useState<"daily" | "weekly" | "monthly">("weekly");
  const [format, setFormat] = useState<"json" | "csv">("json");
  const [lastRunContent, setLastRunContent] = useState<string | null>(null);

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!defaultPortfolioId) return;
    createSchedule.mutate({ portfolio_id: defaultPortfolioId, frequency, format });
  }

  async function handleRunNow(scheduleId: string) {
    const result = await runNow.mutateAsync(scheduleId);
    setLastRunContent(result.content ?? result.message ?? "Data unavailable.");
  }

  const views = mapScheduledReportViews(schedules);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Create Scheduled Report</CardTitle>
        </CardHeader>
        <CardContent>
          {!defaultPortfolioId ? (
            <p className="text-sm text-[var(--muted)]">
              Data unavailable. Create a portfolio first (Portfolio Intelligence Workspace).
            </p>
          ) : (
            <form className="flex flex-wrap items-end gap-3" onSubmit={handleCreate}>
              <div>
                <label className="mb-1 block text-xs text-[var(--muted)]" htmlFor="sched-freq">
                  Frequency
                </label>
                <Select value={frequency} onValueChange={(v) => setFrequency(v as typeof frequency)}>
                  <SelectTrigger id="sched-freq" className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daily">Daily</SelectItem>
                    <SelectItem value="weekly">Weekly</SelectItem>
                    <SelectItem value="monthly">Monthly</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="mb-1 block text-xs text-[var(--muted)]" htmlFor="sched-format">
                  Format
                </label>
                <Select value={format} onValueChange={(v) => setFormat(v as typeof format)}>
                  <SelectTrigger id="sched-format" className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="json">JSON</SelectItem>
                    <SelectItem value="csv">CSV</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button type="submit" disabled={createSchedule.isPending}>
                Add schedule
              </Button>
            </form>
          )}
          <p className="mt-2 text-xs text-[var(--muted)]">
            Schedules run only when you click &quot;Run now&quot; — no autonomous cron executes
            them yet (recorded gap, see documentation).
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Your Scheduled Reports</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : views.length === 0 ? (
            <EmptyState title="No scheduled reports yet" description="Create one above." />
          ) : (
            <ul className="space-y-2" aria-label="Scheduled reports">
              {views.map((schedule) => (
                <li
                  key={schedule.scheduleId}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border)] p-3"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{schedule.frequencyLabel}</Badge>
                      <Badge variant="outline">{schedule.formatLabel}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-[var(--muted)]">
                      Last run: {schedule.lastRunAt}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleRunNow(schedule.scheduleId)}
                      disabled={runNow.isPending}
                    >
                      Run now
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => deleteSchedule.mutate(schedule.scheduleId)}
                    >
                      Delete
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {lastRunContent ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Last run output</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-[var(--radius-md)] bg-[var(--surface-2)] p-3 text-xs">
              {lastRunContent}
            </pre>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

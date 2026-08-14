"use client";

/**
 * Notification Center panel (RC1 Milestone 5) — presentation only. Every
 * notification is created server-side (dsp_platform.workflow_automation)
 * when an alert transitions into "triggered"; this component only lists
 * and marks them read.
 */

import { Badge, Button, Card, CardContent, CardHeader, CardTitle, EmptyState, Skeleton } from "@/components/ds";
import { mapNotificationViews } from "@/lib/workflow-automation/mapWorkflowAutomation";
import { useNotifications } from "@/lib/workflow-automation/useWorkflowAutomation";

export function NotificationCenterPanel({ token }: { token: string | null | undefined }) {
  const { notifications, isLoading, markRead } = useNotifications(token);
  const views = mapNotificationViews(notifications);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Notification Center</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : views.length === 0 ? (
          <EmptyState
            title="No notifications yet"
            description="Triggered alerts will appear here."
          />
        ) : (
          <ul className="space-y-2" aria-label="Notifications">
            {views.map((notification) => (
              <li
                key={notification.notificationId}
                className="flex items-start justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border)] p-3"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{notification.title}</span>
                    {!notification.read ? <Badge variant="accent">New</Badge> : null}
                  </div>
                  <p className="mt-1 text-sm text-[var(--muted)]">{notification.message}</p>
                  <p className="mt-1 text-xs text-[var(--muted)]">{notification.createdAt}</p>
                </div>
                {!notification.read ? (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => markRead.mutate(notification.notificationId)}
                  >
                    Mark read
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

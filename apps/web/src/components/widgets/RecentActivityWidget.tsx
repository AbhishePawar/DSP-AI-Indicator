"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";

export function RecentActivityWidget() {
  return (
    <Card>
      <CardHeader
        title="Recent Activity"
        description="Placeholder — activity feed arrives in a later phase"
      />
      <CardBody>
        <EmptyState
          title="No activity yet"
          description="Session activity will surface here when the backend exposes an activity feed."
        />
      </CardBody>
    </Card>
  );
}

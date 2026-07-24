"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";

export function FavoritesWidget() {
  return (
    <Card>
      <CardHeader
        title="Favorites"
        description="Placeholder — favorites sync in a later phase"
      />
      <CardBody>
        <EmptyState
          title="No favorites"
          description="Saved symbols and workspaces will appear here."
        />
      </CardBody>
    </Card>
  );
}

"use client";

import { Button } from "@/components/ui/Button";

export function RefreshButton({
  onRefresh,
  isRefreshing,
  label = "Refresh",
}: {
  onRefresh: () => void;
  isRefreshing?: boolean;
  label?: string;
}) {
  return (
    <Button
      type="button"
      size="sm"
      variant="secondary"
      onClick={onRefresh}
      disabled={isRefreshing}
      aria-busy={isRefreshing}
    >
      {isRefreshing ? (
        <span className="inline-flex items-center gap-2">
          <span
            className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--accent)]"
            aria-hidden
          />
          Refreshing…
        </span>
      ) : (
        label
      )}
    </Button>
  );
}

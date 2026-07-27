"use client";

import { useMemo, useState, type ReactNode } from "react";

/** Window large lists to reduce DOM / render frequency (Sprint 11 polish). */
export function WindowedList<T>({
  items,
  initial = 12,
  step = 12,
  renderItem,
  empty,
  className = "grid gap-3 md:grid-cols-2",
}: {
  items: T[];
  initial?: number;
  step?: number;
  renderItem: (item: T, index: number) => ReactNode;
  empty?: ReactNode;
  className?: string;
}) {
  const [limit, setLimit] = useState(initial);
  const visible = useMemo(() => items.slice(0, limit), [items, limit]);
  const remaining = Math.max(items.length - visible.length, 0);

  if (items.length === 0) return <>{empty ?? null}</>;

  return (
    <div className="space-y-3">
      <div className={className}>
        {visible.map((item, index) => renderItem(item, index))}
      </div>
      {remaining > 0 ? (
        <button
          type="button"
          className="dsp-interactive min-h-11 rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 text-sm font-medium hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          onClick={() => setLimit((n) => n + step)}
        >
          Show {Math.min(step, remaining)} more ({remaining} remaining)
        </button>
      ) : null}
    </div>
  );
}

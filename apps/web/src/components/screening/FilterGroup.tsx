"use client";

import type { ReactNode } from "react";

export function FilterGroup({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2">
      <label className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
        {label}
      </label>
      {children}
    </div>
  );
}

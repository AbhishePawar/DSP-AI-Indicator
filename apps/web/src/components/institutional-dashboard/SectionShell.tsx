import type { ReactNode } from "react";

import { Card, CardContent } from "@/components/ds";

export function SectionShell({
  id,
  title,
  description,
  children,
  prominent = false,
}: {
  id: string;
  title: string;
  description?: string;
  children: ReactNode;
  prominent?: boolean;
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-heading`}
      className="scroll-mt-24"
    >
      <Card
        className={
          prominent ? "border-[var(--accent)]/50 shadow-sm" : undefined
        }
      >
        <div className="border-b border-[var(--border)] px-4 py-3">
          <h2
            id={`${id}-heading`}
            className="font-[family-name:var(--font-display)] text-lg tracking-tight"
          >
            {title}
          </h2>
          {description ? (
            <p className="mt-0.5 text-sm text-[var(--muted)]">{description}</p>
          ) : null}
        </div>
        <CardContent className="space-y-4">{children}</CardContent>
      </Card>
    </section>
  );
}

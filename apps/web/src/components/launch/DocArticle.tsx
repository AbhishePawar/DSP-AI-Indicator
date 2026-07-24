"use client";

import Link from "next/link";

import { Card, CardBody } from "@/components/ui/Card";

export function DocArticle({
  title,
  sections,
}: {
  title: string;
  sections: { heading: string; body: string[] }[];
}) {
  return (
    <article className="space-y-4">
      <p className="text-sm">
        <Link className="text-[var(--accent)] underline" href="/docs">
          ← Documentation
        </Link>
      </p>
      <h1 className="font-[family-name:var(--font-display)] text-3xl tracking-tight">{title}</h1>
      {sections.map((s) => (
        <Card key={s.heading}>
          <CardBody className="space-y-2 text-sm">
            <h2 className="font-[family-name:var(--font-display)] text-lg">{s.heading}</h2>
            {s.body.map((p) => (
              <p key={p} className="text-[var(--muted)]">
                {p}
              </p>
            ))}
          </CardBody>
        </Card>
      ))}
    </article>
  );
}

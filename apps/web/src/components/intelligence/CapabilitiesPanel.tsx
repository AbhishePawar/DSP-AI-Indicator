"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";

export function CapabilitiesPanel({
  modules,
  stages,
  reports,
  platformCapabilities,
}: {
  modules?: string[];
  stages?: string[];
  reports?: string[];
  platformCapabilities?: string[];
}) {
  return (
    <Card>
      <CardHeader
        title="Capabilities"
        description="From GET /api/v1/capabilities"
      />
      <CardBody className="grid gap-4 md:grid-cols-2">
        <List title="Pipeline stages" items={stages} />
        <List title="Analytical modules" items={modules} />
        <List title="Supported reports" items={reports} />
        <List title="Platform capabilities" items={platformCapabilities} />
      </CardBody>
    </Card>
  );
}

function List({ title, items }: { title: string; items?: string[] }) {
  return (
    <div>
      <h4 className="text-sm font-medium">{title}</h4>
      {items?.length ? (
        <ul className="mt-2 list-inside list-disc text-sm text-[var(--muted)]">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-[var(--muted)]">Unavailable</p>
      )}
    </div>
  );
}

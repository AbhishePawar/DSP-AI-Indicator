"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";

export function VersionCard({
  apiVersion,
  apiPackageVersion,
  platformVersion,
  pipelineVersion,
  docsVersion,
}: {
  apiVersion?: string;
  apiPackageVersion?: string;
  platformVersion?: string;
  pipelineVersion?: string;
  docsVersion?: string;
}) {
  const rows = [
    ["API label", apiVersion],
    ["API package", apiPackageVersion],
    ["Platform", platformVersion],
    ["Pipeline", pipelineVersion],
    ["Docs suite", docsVersion],
  ];
  return (
    <Card>
      <CardHeader
        title="Version Information"
        description="From GET /api/v1/version"
      />
      <CardBody>
        <dl className="grid gap-2 sm:grid-cols-2">
          {rows.map(([label, value]) => (
            <div key={label}>
              <dt className="text-xs text-[var(--muted)]">{label}</dt>
              <dd className="font-medium">{value || "Unavailable"}</dd>
            </div>
          ))}
        </dl>
      </CardBody>
    </Card>
  );
}

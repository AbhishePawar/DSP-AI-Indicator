"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { CompanyEntry } from "@/lib/companies/catalogue";
import { CompanyGrid } from "./CompanyGrid";

export function CompanyCategory({
  title,
  description,
  companies,
  placeholder,
}: {
  title: string;
  description?: string;
  companies?: CompanyEntry[];
  placeholder?: string;
}) {
  return (
    <section aria-label={title}>
      {companies && companies.length > 0 ? (
        <div className="space-y-3">
          <div>
            <h2 className="font-[family-name:var(--font-display)] text-xl tracking-tight">
              {title}
            </h2>
            {description ? (
              <p className="mt-0.5 text-sm text-[var(--muted)]">{description}</p>
            ) : null}
          </div>
          <CompanyGrid companies={companies} />
        </div>
      ) : (
        <Card>
          <CardHeader title={title} description={description} />
          <CardBody>
            <p className="text-sm text-[var(--muted)]">
              {placeholder ?? "No items yet."}
            </p>
          </CardBody>
        </Card>
      )}
    </section>
  );
}

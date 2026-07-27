"use client";

import type { CompanyEntry } from "@/lib/companies/catalogue";
import { CompanyGrid } from "@/components/companies/CompanyGrid";

export function ScreeningResults({
  companies,
}: {
  companies: CompanyEntry[];
}) {
  return <CompanyGrid companies={companies} />;
}

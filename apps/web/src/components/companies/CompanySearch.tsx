"use client";

import { Input } from "@/components/ui/Input";

export function CompanySearch({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="relative">
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search by company name or ticker…"
        aria-label="Search companies"
        className="w-full"
      />
    </div>
  );
}

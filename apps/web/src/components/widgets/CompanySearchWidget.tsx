"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { SearchBox } from "@/components/ui/SearchBox";

export function CompanySearchWidget() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  return (
    <Card>
      <CardHeader
        title="Company Search"
        description="Opens Company Analysis with a symbol — analysis runs on the API"
      />
      <CardBody>
        <SearchBox
          value={query}
          onChange={setQuery}
          label="Company symbol"
          placeholder="Symbol e.g. AAPL"
          onSubmit={() => {
            const symbol = query.trim().toUpperCase();
            if (!symbol) {
              router.push("/analysis");
              return;
            }
            router.push(`/analysis?symbol=${encodeURIComponent(symbol)}`);
          }}
        />
      </CardBody>
    </Card>
  );
}

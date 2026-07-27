"use client";

import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";

export function EmptyPortfolio() {
  return (
    <Card>
      <CardBody className="flex flex-col items-center justify-center px-6 py-16 text-center">
        <p className="font-[family-name:var(--font-display)] text-2xl tracking-tight">
          Your portfolio is empty.
        </p>
        <p className="mt-2 max-w-md text-sm text-[var(--muted)]">
          Browse companies to begin building your portfolio.
        </p>
        <Link href="/companies" className="mt-6">
          <Button>Browse Companies</Button>
        </Link>
      </CardBody>
    </Card>
  );
}

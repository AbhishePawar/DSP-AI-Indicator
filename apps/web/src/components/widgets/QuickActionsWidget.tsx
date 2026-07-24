"use client";

import Link from "next/link";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

const ACTIONS = [
  { href: "/analysis", label: "Analyze Company" },
  { href: "/portfolio", label: "Portfolio Intelligence" },
  { href: "/launch", label: "Launch Dashboard" },
  { href: "/docs", label: "Documentation" },
] as const;

export function QuickActionsWidget() {
  return (
    <Card>
      <CardHeader
        title="Quick Actions"
        description="Jump to primary workspaces"
      />
      <CardBody className="grid gap-2 sm:grid-cols-2">
        {ACTIONS.map((action) => (
          <Link key={action.href} href={action.href}>
            <Button variant="secondary" className="w-full justify-start">
              {action.label}
            </Button>
          </Link>
        ))}
      </CardBody>
    </Card>
  );
}

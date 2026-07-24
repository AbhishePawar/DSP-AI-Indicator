"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { isAdvisorDemoEnabled } from "@/lib/advisor/isAdvisorDemoEnabled";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";

export function AdvisorDemoGate({ children }: { children: ReactNode }) {
  if (!isAdvisorDemoEnabled()) {
    return (
      <Card>
        <CardHeader title="Advisor demo disabled" />
        <CardBody className="space-y-3 text-sm">
          <p className="text-[var(--muted)]">
            The Advisor Platform is optional. Enable demo mode with{" "}
            <code className="text-xs">NEXT_PUBLIC_ADVISOR_DEMO=true</code> to explore the foundation
            workspace. Single-user research experience remains unchanged when disabled.
          </p>
          <Link href="/dashboard">
            <Button variant="secondary">Back to Dashboard</Button>
          </Link>
        </CardBody>
      </Card>
    );
  }
  return <>{children}</>;
}

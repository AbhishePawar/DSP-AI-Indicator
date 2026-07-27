"use client";

import Link from "next/link";

import { PreferenceManager } from "@/components/persistence/PreferenceManager";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { env } from "@/lib/env";

export default function SettingsPage() {
  return (
    <div>
      <PageHeader
        title="Settings"
        description="Client preferences and platform information."
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <PreferenceManager />
        <Card>
          <CardHeader title="Environment" />
          <CardBody className="space-y-2 font-mono text-sm">
            <Row label="Version" value={`v${env.frontendVersion}`} />
            <Row label="Environment" value={env.environment} />
            <Row label="API Base URL" value={env.apiBaseUrl} />
            <div className="pt-2">
              <Link href="/diagnostics">
                <Button variant="secondary" size="sm">
                  Open diagnostics
                </Button>
              </Link>
            </div>
          </CardBody>
        </Card>
        <Card className="sm:col-span-2">
          <CardHeader title="About DSP AI Indicator" />
          <CardBody className="text-sm text-[var(--muted)]">
            <p>
              Professional investment research platform. Explainable AI decision
              support over frozen analytical APIs. The frontend is a presentation
              boundary only — no business logic runs in the browser.
            </p>
            <p className="mt-2">
              Architecture: Next.js thin client → /api/v1 → dsp_platform →
              FEATURE domain engines.
            </p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-[var(--muted)]">{label}</span>
      <span className="truncate">{value}</span>
    </div>
  );
}

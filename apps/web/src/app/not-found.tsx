import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <Card>
        <CardHeader title="404 — Page not found" description="Unknown route" />
        <CardBody className="space-y-4">
          <p className="text-sm text-[var(--muted)]">
            That route is not part of the DSP terminal surface. No research data
            was changed.
          </p>
          <div className="flex flex-wrap gap-2">
            <Link href="/dashboard">
              <Button>Go to dashboard</Button>
            </Link>
            <Link href="/diagnostics">
              <Button variant="secondary">Diagnostics</Button>
            </Link>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}

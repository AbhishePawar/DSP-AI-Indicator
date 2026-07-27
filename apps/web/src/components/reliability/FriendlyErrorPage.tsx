import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";

export function FriendlyErrorPage({
  code,
  title,
  message,
  detail,
  showDashboardLink = true,
  onRetry,
}: {
  code?: string;
  title: string;
  message: string;
  detail?: string;
  showDashboardLink?: boolean;
  onRetry?: () => void;
}) {
  return (
    <div className="mx-auto max-w-lg space-y-4 px-4 py-12">
      <Card className="border-[var(--danger-border)]">
        <CardHeader
          title={code ? `${code} — ${title}` : title}
          description="Graceful degradation"
        />
        <CardBody className="space-y-3">
          <p className="text-sm">{message}</p>
          {detail ? (
            <p className="rounded-md bg-[var(--surface-2)] px-3 py-2 font-mono text-xs text-[var(--muted)]">
              {detail}
            </p>
          ) : null}
          <p className="text-xs text-[var(--muted)]">
            Research engines and API contracts were not modified. No investment
            data was changed by this error.
          </p>
          <div className="flex flex-wrap gap-2">
            {onRetry ? (
              <Button type="button" onClick={onRetry}>
                Try again
              </Button>
            ) : null}
            {showDashboardLink ? (
              <Link href="/dashboard">
                <Button variant="secondary">Go to dashboard</Button>
              </Link>
            ) : null}
            <Link href="/diagnostics">
              <Button variant="secondary">View diagnostics</Button>
            </Link>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}

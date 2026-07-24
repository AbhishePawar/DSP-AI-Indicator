import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";

export default function MaintenancePage() {
  return (
    <div>
      <PageHeader
        title="Maintenance"
        description="Scheduled maintenance placeholder for Private Beta operations."
      />
      <Card>
        <CardHeader title="Platform temporarily unavailable" />
        <CardBody className="space-y-3 text-sm">
          <p>
            DSP may be offline for maintenance. Research engines and valuations are not running
            client-side — please retry when the banner clears.
          </p>
          <Link href="/dashboard" className="text-[var(--accent)] underline">
            Return to dashboard
          </Link>
        </CardBody>
      </Card>
    </div>
  );
}

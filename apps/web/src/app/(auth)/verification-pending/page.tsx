import type { Metadata } from "next";
import Link from "next/link";

import { AuthCard, AuthShell } from "@/components/auth";
import { Alert, Button, EmptyState, Stack } from "@/components/ds";
import { SUPPORT_CONTACT } from "@/lib/commercial";

export const metadata: Metadata = {
  title: "Verification pending",
};

export default function VerificationPendingPage() {
  return (
    <AuthShell>
      <AuthCard
        title="Access pending"
        description="Waiting on administrator provisioning — not an automated verification queue."
      >
        <Stack gap={4}>
          <EmptyState
            title="Administrator action required"
            description="Data unavailable for automated verification status. If you requested access, wait for your administrator to provision the account, then sign in."
            action={
              <div className="flex flex-wrap justify-center gap-2">
                <Link href="/login">
                  <Button>Sign in</Button>
                </Link>
                <Link href="/signup">
                  <Button variant="secondary">Request access details</Button>
                </Link>
              </div>
            }
          />
          <Alert variant="info" title="What happens next">
            Provisioning is organisation-controlled in this release. There is no
            email-verification service to poll.
          </Alert>
          <p className="text-xs text-[var(--muted)]">
            {SUPPORT_CONTACT.channelsPublished
              ? `Support: ${SUPPORT_CONTACT.email}`
              : SUPPORT_CONTACT.unpublishedNote}
          </p>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}

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
        title="Verification pending"
        description="Your account access is waiting on administrator action or email confirmation."
      >
        <Stack gap={4}>
          <EmptyState
            title="Nothing to verify yet"
            description="Data unavailable for automated status. If you just requested access, wait for your administrator. If you already have a code, continue to email verification."
            action={
              <div className="flex flex-wrap justify-center gap-2">
                <Link href="/verify-email">
                  <Button>Enter verification code</Button>
                </Link>
                <Link href="/login">
                  <Button variant="secondary">Sign in</Button>
                </Link>
              </div>
            }
          />
          <Alert variant="info" title="What happens next">
            Provisioning and email confirmation are organisation-controlled in
            this release. Contact{" "}
            <a
              className="underline"
              href={`mailto:${SUPPORT_CONTACT.email}`}
            >
              {SUPPORT_CONTACT.email}
            </a>{" "}
            if you are blocked longer than expected.
          </Alert>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}

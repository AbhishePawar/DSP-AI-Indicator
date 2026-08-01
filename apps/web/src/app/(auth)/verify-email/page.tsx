import type { Metadata } from "next";
import Link from "next/link";

import { AuthCard, AuthShell } from "@/components/auth";
import { Alert, Button, EmptyState, Stack } from "@/components/ds";
import { SUPPORT_CONTACT } from "@/lib/commercial";

export const metadata: Metadata = {
  title: "Email verification",
};

/**
 * RC3-002 — No fake verification success. Email verification service unavailable.
 */
export default function VerifyEmailPage() {
  return (
    <AuthShell>
      <AuthCard
        title="Email verification"
        description="Automated email verification is not available in this release."
      >
        <Stack gap={4}>
          <EmptyState
            title="Verification service unavailable"
            description="DSP does not validate email verification codes through this interface. Account activation is confirmed by your administrator — not by submitting a code here."
            action={
              <div className="flex flex-wrap justify-center gap-2">
                <Link href="/login">
                  <Button>Sign in when provisioned</Button>
                </Link>
                <Link href="/signup">
                  <Button variant="secondary">Request access</Button>
                </Link>
              </div>
            }
          />
          <Alert variant="info" title="Honest status">
            No verification API runs on this page. Do not treat any prior local
            capture as confirmed email.
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

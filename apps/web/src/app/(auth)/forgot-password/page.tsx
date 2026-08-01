import type { Metadata } from "next";
import Link from "next/link";

import { AuthCard, AuthShell } from "@/components/auth";
import { Alert, Button, EmptyState, Stack } from "@/components/ds";
import { SUPPORT_CONTACT } from "@/lib/commercial";

export const metadata: Metadata = {
  title: "Forgot password",
};

/**
 * RC3-002 — Honest password help. No reset API; no simulated emails.
 */
export default function ForgotPasswordPage() {
  return (
    <AuthShell>
      <AuthCard
        title="Forgot password"
        description="Password reset requests are currently handled by an administrator."
      >
        <Stack gap={4}>
          <EmptyState
            title="Self-service reset is not available"
            description="The platform does not send password-reset emails in this release. Ask your organisation administrator to restore access."
            action={
              <Link href="/login">
                <Button>Back to sign in</Button>
              </Link>
            }
          />
          <Alert variant="info" title="How to regain access">
            Contact your programme administrator with your username or work
            email. Do not expect an automated reset message from DSP.
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

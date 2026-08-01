import type { Metadata } from "next";
import Link from "next/link";

import { AuthCard, AuthShell } from "@/components/auth";
import { Alert, Button, EmptyState, Stack } from "@/components/ds";
import { SUPPORT_CONTACT } from "@/lib/commercial";

export const metadata: Metadata = {
  title: "Reset password",
};

/**
 * RC3-002 — No offline token theatre. Password changes are administrator-handled.
 */
export default function ResetPasswordPage() {
  return (
    <AuthShell>
      <AuthCard
        title="Reset password"
        description="Automated password change is not available in this release."
      >
        <Stack gap={4}>
          <EmptyState
            title="Password changes require an administrator"
            description="There is no password-reset API on this release. Your administrator must issue or update credentials. This page does not accept or validate reset tokens."
            action={
              <div className="flex flex-wrap justify-center gap-2">
                <Link href="/forgot-password">
                  <Button variant="secondary">Password help</Button>
                </Link>
                <Link href="/login">
                  <Button>Sign in</Button>
                </Link>
              </div>
            }
          />
          <Alert variant="warning" title="No simulated reset">
            Entering a token or new password here would not change your account.
            The form has been removed to avoid misleading workflows.
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

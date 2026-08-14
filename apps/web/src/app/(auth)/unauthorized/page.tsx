import type { Metadata } from "next";
import Link from "next/link";

import { AuthCard, AuthShell } from "@/components/auth";
import { Button, ErrorState, Stack } from "@/components/ds";

export const metadata: Metadata = {
  title: "Unauthorized",
};

/** HTTP 401 experience — unauthenticated / invalid token. */
export default function UnauthorizedPage() {
  return (
    <AuthShell>
      <AuthCard
        title="Unauthorized"
        description="Authentication is required, or the presented credentials are invalid (HTTP 401)."
      >
        <ErrorState
          title="Sign in required"
          description="This resource needs a valid session. If you believe you should have access, sign in again or contact your administrator."
          action={
            <Stack gap={2} className="items-center">
              <Link href="/login">
                <Button>Sign in</Button>
              </Link>
              <Link
                href="/session-expired"
                className="text-sm text-[var(--muted)] underline-offset-2 hover:underline"
              >
                Session expired help
              </Link>
            </Stack>
          }
        />
      </AuthCard>
    </AuthShell>
  );
}

import type { Metadata } from "next";
import Link from "next/link";

import { AuthCard, AuthShell } from "@/components/auth";
import { Alert, Button, Stack } from "@/components/ds";

export const metadata: Metadata = {
  title: "Forbidden",
};

export default function ForbiddenPage() {
  return (
    <AuthShell>
      <AuthCard
        title="Access forbidden"
        description="You do not have permission to view this resource."
      >
        <Stack gap={4}>
          <Alert variant="warning" title="Insufficient privileges">
            Your account is authenticated but lacks the required role or
            permission. Contact an administrator if you believe this is an
            error.
          </Alert>
          <div className="flex flex-wrap gap-2">
            <Link href="/dashboard">
              <Button>Research dashboard</Button>
            </Link>
            <Link href="/login">
              <Button variant="secondary">Sign in as another user</Button>
            </Link>
          </div>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}

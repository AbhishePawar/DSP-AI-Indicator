import type { Metadata } from "next";
import Link from "next/link";

import { AuthCard, AuthShell } from "@/components/auth";
import { Button, EmptyState } from "@/components/ds";

export const metadata: Metadata = {
  title: "Forbidden",
};

/** HTTP 403 experience — authenticated but missing permission. */
export default function ForbiddenPage() {
  return (
    <AuthShell>
      <AuthCard
        title="Forbidden"
        description="You are signed in, but you do not have permission for this resource (HTTP 403)."
      >
        <EmptyState
          title="Permission required"
          description="Data unavailable for the requested action under your current roles. Return to the dashboard or review your profile with an administrator."
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <Link href="/dashboard">
                <Button variant="secondary">Dashboard</Button>
              </Link>
              <Link href="/profile">
                <Button>View profile</Button>
              </Link>
              <Link href="/logout">
                <Button variant="ghost">Sign out</Button>
              </Link>
            </div>
          }
        />
      </AuthCard>
    </AuthShell>
  );
}

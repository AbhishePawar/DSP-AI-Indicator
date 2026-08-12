"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AuthCard, AuthShell } from "@/components/auth";
import { Button, ErrorState, Stack } from "@/components/ds";
import { WorkspaceLoading } from "@/components/loading/WorkspaceLoading";

function SessionExpiredContent() {
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const loginHref = next
    ? `/login?expired=1&next=${encodeURIComponent(next)}`
    : "/login?expired=1";

  return (
    <AuthShell>
      <AuthCard
        title="Session expired"
        description="Your authentication session is no longer valid. Sign in again to continue research work."
      >
        <ErrorState
          title="Please sign in again"
          description="For security, idle or invalidated sessions cannot continue. Your intended destination will be restored after login when available."
          action={
            <Stack gap={2} className="items-center">
              <Link href={loginHref}>
                <Button>Sign in</Button>
              </Link>
              <Link
                href="/dashboard"
                className="text-sm text-[var(--muted)] underline-offset-2 hover:underline"
              >
                Continue on public research routes
              </Link>
            </Stack>
          }
        />
      </AuthCard>
    </AuthShell>
  );
}

export default function SessionExpiredPage() {
  return (
    <Suspense
      fallback={
        <AuthShell>
          <AuthCard title="Session expired" description="Loading…">
            <WorkspaceLoading label="Loading…" />
          </AuthCard>
        </AuthShell>
      }
    >
      <SessionExpiredContent />
    </Suspense>
  );
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AuthCard, AuthShell } from "@/components/auth";
import { Alert, Button, Stack, SuccessState } from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";

/** Secure logout confirmation experience. */
export default function LogoutPage() {
  const router = useRouter();
  const { logout, session, status } = useAuth();
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const restoring = status === "restoring";
  const signedIn = status === "authenticated" && Boolean(session);

  async function confirmLogout() {
    setPending(true);
    setError(null);
    try {
      await logout();
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-out failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthShell>
      <AuthCard
        title="Sign out"
        description="End your research session on this device. Local session data for your subject is cleared after confirmation."
      >
        <Stack gap={4}>
          {restoring ? (
            <SuccessState
              title="Restoring session"
              description="Checking your current authenticated session. Please wait…"
            />
          ) : done || !signedIn ? (
            <SuccessState
              title={done ? "Signed out" : "No active session"}
              description={
                done
                  ? "You have left the authenticated platform. You can return to the marketing site or sign in again."
                  : "There is no authenticated session on this device."
              }
              action={
                <div className="flex flex-wrap justify-center gap-2">
                  <Link href="/login">
                    <Button>Sign in</Button>
                  </Link>
                  <Link href="/">
                    <Button variant="secondary">Marketing site</Button>
                  </Link>
                </div>
              }
            />
          ) : (
            <>
              <Alert variant="warning" title="Confirm sign out">
                You are signed in as{" "}
                <strong className="text-[var(--fg)]">
                  {session?.username || session?.subject || "user"}
                </strong>
                . Signing out ends RBAC session use on this browser.
              </Alert>
              {error ? (
                <p className="text-sm text-[var(--danger-fg)]" role="alert">
                  {error}
                </p>
              ) : null}
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => void confirmLogout()}
                  disabled={pending}
                  variant="danger"
                >
                  {pending ? "Signing out…" : "Confirm sign out"}
                </Button>
                <Button
                  variant="secondary"
                  disabled={pending}
                  onClick={() => router.back()}
                >
                  Cancel
                </Button>
              </div>
            </>
          )}
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}

"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { AuthCard, AuthShell, MfaChallenge, mapAuthError } from "@/components/auth";
import { Alert, Button, Spinner, Stack } from "@/components/ds";
import { WorkspaceLoading } from "@/components/loading/WorkspaceLoading";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import { normalizePath } from "@/lib/auth/routeGuards";
import {
  extractMfaChallenge,
  navigateAfterLogin,
  persistEnterpriseSession,
} from "@/lib/auth/finishEnterpriseSession";
import type { MfaChallengeInfo } from "@/lib/auth/types";

function EmailLoginVerifyInner() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const nextPath = normalizePath(searchParams.get("next") || "/dashboard");

  const [status, setStatus] = useState<"pending" | "error" | "done">("pending");
  const [error, setError] = useState<string | null>(null);
  const [mfaChallenge, setMfaChallenge] = useState<MfaChallengeInfo | null>(null);

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setError("Missing sign-in token.");
      return;
    }
    let cancelled = false;
    enterpriseAuthApi
      .verifyEmailLink({ token, remember_me: false })
      .then((envelope) => {
        if (cancelled) return;
        if (!envelope.ok || !envelope.result) {
          throw new Error(envelope.error || "This link is invalid or expired.");
        }
        persistEnterpriseSession(envelope.result, false);
        const challenge = extractMfaChallenge(envelope.result);
        if (challenge) {
          setMfaChallenge(challenge);
          setStatus("done");
        } else {
          navigateAfterLogin(nextPath);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setStatus("error");
        setError(mapAuthError(err));
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <AuthCard title="Signing you in" description="Verifying your email sign-in link.">
      <Stack gap={4}>
        {status === "pending" ? (
          <Spinner label="Verifying link…" />
        ) : status === "error" ? (
          <>
            <Alert variant="error" title="Sign-in link failed">
              {error}
            </Alert>
            <Link href="/email-login">
              <Button className="w-full">Request a new link</Button>
            </Link>
          </>
        ) : mfaChallenge ? (
          <MfaChallenge challenge={mfaChallenge} onDone={() => navigateAfterLogin(nextPath)} />
        ) : null}
      </Stack>
    </AuthCard>
  );
}

export default function EmailLoginVerifyPage() {
  return (
    <AuthShell>
      <Suspense
        fallback={
          <AuthCard title="Signing you in" description="Loading…">
            <WorkspaceLoading label="Loading…" />
          </AuthCard>
        }
      >
        <EmailLoginVerifyInner />
      </Suspense>
    </AuthShell>
  );
}

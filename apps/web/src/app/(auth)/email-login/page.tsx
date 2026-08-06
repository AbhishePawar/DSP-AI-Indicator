import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthCard, AuthShell } from "@/components/auth";
import { WorkspaceLoading } from "@/components/loading/WorkspaceLoading";

import EmailLoginForm from "./EmailLoginForm";

export const metadata: Metadata = {
  title: "Sign in with email",
};

export default function EmailLoginPage() {
  return (
    <Suspense
      fallback={
        <AuthShell>
          <AuthCard title="Sign in with email" description="Loading…">
            <WorkspaceLoading label="Loading email sign-in…" />
          </AuthCard>
        </AuthShell>
      }
    >
      <EmailLoginForm />
    </Suspense>
  );
}

import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthCard, AuthShell } from "@/components/auth";
import { WorkspaceLoading } from "@/components/loading/WorkspaceLoading";

import LoginForm from "./LoginForm";

export const metadata: Metadata = {
  title: "Sign in",
  description: "Login with password or Google",
};

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <AuthShell>
          <AuthCard title="Sign in" description="Loading sign-in form…">
            <WorkspaceLoading label="Loading sign in…" />
          </AuthCard>
        </AuthShell>
      }
    >
      <LoginForm />
    </Suspense>
  );
}

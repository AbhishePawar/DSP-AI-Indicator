import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthCard, AuthShell } from "@/components/auth";
import { WorkspaceLoading } from "@/components/loading/WorkspaceLoading";

import MobileLoginForm from "./MobileLoginForm";

export const metadata: Metadata = {
  title: "Sign in with mobile",
};

export default function MobileLoginPage() {
  return (
    <Suspense
      fallback={
        <AuthShell>
          <AuthCard title="Sign in with mobile" description="Loading…">
            <WorkspaceLoading label="Loading mobile sign-in…" />
          </AuthCard>
        </AuthShell>
      }
    >
      <MobileLoginForm />
    </Suspense>
  );
}

import { Suspense } from "react";

import { WorkspaceLoading } from "@/components/loading/WorkspaceLoading";
import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="grid min-h-screen place-items-center px-4">
          <WorkspaceLoading label="Loading sign in…" />
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}

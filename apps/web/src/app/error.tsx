"use client";

import { useEffect } from "react";

import { RetryCard } from "@/components/reliability/RetryCard";
import { GracefulDegradationCard } from "@/components/reliability/RetryCard";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[DSP route error]", error.message, error.digest);
  }, [error]);

  return (
    <div className="mx-auto max-w-lg space-y-4 px-4 py-12">
      <h1 className="sr-only">Application error</h1>
      <GracefulDegradationCard
        title="500 — Unexpected application error"
        message="A route failed to render. Retry the page. Product engines were not modified."
      />
      <RetryCard detail={error.message} onRetry={reset} />
    </div>
  );
}

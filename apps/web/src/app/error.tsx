"use client";

import { useEffect } from "react";

import { FriendlyErrorPage } from "@/components/reliability/FriendlyErrorPage";
import { logger } from "@/lib/observability/logger";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    logger.recordClientError(error, "route-error", { digest: error.digest });
  }, [error]);

  return (
    <FriendlyErrorPage
      code="500"
      title="Unexpected application error"
      message="A route failed to render. Retry the page or return to the dashboard."
      detail={error.message}
      onRetry={reset}
    />
  );
}

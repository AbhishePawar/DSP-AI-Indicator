"use client";

import { useEffect } from "react";

import { logger } from "@/lib/observability/logger";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    logger.recordClientError(error, "global-route-error", {
      digest: error.digest,
    });
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          fontFamily: "system-ui, sans-serif",
          background: "#0f1419",
          color: "#e8eaed",
          margin: 0,
          padding: 24,
        }}
      >
        <main style={{ maxWidth: 480, margin: "48px auto" }}>
          <p style={{ fontSize: 12, opacity: 0.7 }}>Critical error</p>
          <h1 style={{ fontSize: 24, marginTop: 8 }}>
            DSP critically failed to load
          </h1>
          <p style={{ marginTop: 12, fontSize: 14, lineHeight: 1.5 }}>
            The application shell could not render. Research engines and APIs were
            not modified.
          </p>
          <p
            style={{
              marginTop: 12,
              padding: 12,
              background: "#1a222c",
              borderRadius: 8,
              fontSize: 12,
              fontFamily: "monospace",
            }}
          >
            {error.message}
          </p>
          <button
            type="button"
            onClick={reset}
            style={{
              marginTop: 16,
              padding: "10px 16px",
              borderRadius: 6,
              border: "none",
              background: "#3d8bfd",
              color: "#fff",
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}

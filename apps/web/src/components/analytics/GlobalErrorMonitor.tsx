"use client";

import { useEffect } from "react";
import { installGlobalErrorHandlers } from "@/lib/observability/errorReporter";

/**
 * GlobalErrorMonitor — installs window-level error handlers once on mount.
 * Renders nothing; purely a side-effect component.
 */
export function GlobalErrorMonitor() {
  useEffect(() => {
    installGlobalErrorHandlers();
  }, []);

  return null;
}

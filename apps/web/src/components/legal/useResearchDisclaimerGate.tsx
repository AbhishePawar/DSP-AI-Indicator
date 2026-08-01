"use client";

import { useCallback, useRef, useState } from "react";

import { ResearchDisclaimerGate } from "@/components/legal/ResearchDisclaimerGate";
import { isResearchDisclaimerAcknowledged } from "@/lib/legal";

/**
 * Wraps report-generation actions so the first run requires disclaimer acknowledgement.
 */
export function useResearchDisclaimerGate() {
  const [open, setOpen] = useState(false);
  const pendingRef = useRef<(() => void) | null>(null);

  const runWithDisclaimer = useCallback((action: () => void) => {
    if (isResearchDisclaimerAcknowledged()) {
      action();
      return;
    }
    pendingRef.current = action;
    setOpen(true);
  }, []);

  const onAcknowledged = useCallback(() => {
    const pending = pendingRef.current;
    pendingRef.current = null;
    pending?.();
  }, []);

  const gate = (
    <ResearchDisclaimerGate
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) pendingRef.current = null;
      }}
      onAcknowledged={onAcknowledged}
    />
  );

  return { runWithDisclaimer, gate };
}

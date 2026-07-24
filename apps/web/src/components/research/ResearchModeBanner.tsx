"use client";

import { Alert } from "@/components/ui/Alert";
import { isResearchOnly } from "@/lib/featureFlags";
import { RESEARCH_DISCLAIMER } from "@/lib/product";

/** Research Mode banner — shown when SEBI recommendation UI is inactive. */
export function ResearchModeBanner() {
  if (!isResearchOnly()) return null;
  return (
    <Alert tone="info" title="Research Mode">
      {RESEARCH_DISCLAIMER}
    </Alert>
  );
}

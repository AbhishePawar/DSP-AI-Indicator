import type { ReactNode } from "react";

import { AdvisorDemoGate } from "@/components/advisor/AdvisorDemoGate";
import { SectionErrorBoundary } from "@/components/reliability/GlobalErrorBoundary";

export default function AdvisorLayout({ children }: { children: ReactNode }) {
  return (
    <SectionErrorBoundary title="Advisor platform">
      <AdvisorDemoGate>{children}</AdvisorDemoGate>
    </SectionErrorBoundary>
  );
}

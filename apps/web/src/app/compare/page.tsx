"use client";

/**
 * Legacy /compare stub — redirects to institutional comparison workspace.
 */

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { WorkspaceSkeleton } from "@/components/company-comparison";

export default function CompareRedirectPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const symbols =
      searchParams.get("symbols") ||
      searchParams.get("symbol") ||
      "";
    const qs = symbols
      ? `?symbols=${encodeURIComponent(symbols)}`
      : "";
    router.replace(`/analysis/compare${qs}`);
  }, [router, searchParams]);

  return <WorkspaceSkeleton />;
}

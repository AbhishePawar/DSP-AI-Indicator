import { Suspense } from "react";

import AnalysisClient from "./AnalysisClient";
import { Skeleton } from "@/components/ui/Skeleton";

export default function AnalysisRoute() {
  return (
    <Suspense
      fallback={
        <div className="space-y-4" aria-busy="true">
          <Skeleton className="h-10 w-1/3" />
          <Skeleton className="h-40 w-full" />
        </div>
      }
    >
      <AnalysisClient />
    </Suspense>
  );
}

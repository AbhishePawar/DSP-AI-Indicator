import { Suspense } from "react";

import AnalysisClient from "./AnalysisClient";

export default function AnalysisPage() {
  return (
    <Suspense fallback={<main className="p-8">Loading research workspace…</main>}>
      <AnalysisClient />
    </Suspense>
  );
}

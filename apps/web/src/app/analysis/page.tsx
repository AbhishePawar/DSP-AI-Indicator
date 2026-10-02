"use client";

import dynamic from "next/dynamic";

function AnalysisSkeleton() {
  return (
    <main className="min-h-screen bg-[var(--bg)] px-6 py-10">
      <div className="mx-auto max-w-6xl animate-pulse space-y-6">
        <div className="h-8 w-56 rounded bg-[var(--surface-2)]" />
        <div className="h-32 rounded-3xl bg-[var(--surface-2)]" />
        <div className="h-48 rounded-3xl bg-[var(--surface-2)]" />
      </div>
    </main>
  );
}

const ZipCompanyAnalysisWorkspace = dynamic(
  () =>
    import("@/components/company-analysis/ZipCompanyAnalysisWorkspace").then((module) => ({
      default: module.ZipCompanyAnalysisWorkspace,
    })),
  {
    ssr: false,
    loading: () => <AnalysisSkeleton />,
  }
);

export default function AnalysisRoute() {
  return <ZipCompanyAnalysisWorkspace />;
}

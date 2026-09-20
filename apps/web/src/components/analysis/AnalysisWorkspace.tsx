"use client";

import { ResearchChatLoading, ResearchChatShell } from "@/components/analysis/ResearchChatShell";
import type { AnalysisWorkspaceView } from "@/lib/analysis/types";

export function AnalysisWorkspace({
  view,
  loading,
  onRefresh,
}: {
  view: AnalysisWorkspaceView;
  loading: boolean;
  onRefresh: () => void;
  onShare?: () => void;
  onReopenSaved?: (
    view: AnalysisWorkspaceView,
    meta: { ticker: string; name: string },
  ) => void;
}) {
  if (loading) return <ResearchChatLoading />;
  return <ResearchChatShell view={view} loading={loading} onRefresh={onRefresh} />;
}

export default AnalysisWorkspace;

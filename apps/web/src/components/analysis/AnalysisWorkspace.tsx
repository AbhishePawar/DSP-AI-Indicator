"use client";

import { ResearchChatLoading, ResearchChatShell } from "@/components/analysis/ResearchChatShell";
import type { AnalysisWorkspaceView } from "@/lib/analysis/types";

export function AnalysisWorkspace({
  view,
  loading,
  symbol,
  onSymbolChange,
  onResearch,
  onRefresh,
}: {
  view: AnalysisWorkspaceView;
  loading: boolean;
  symbol: string;
  onSymbolChange: (value: string) => void;
  onResearch: () => void;
  onRefresh: () => void;
  onShare?: () => void;
  onReopenSaved?: (
    view: AnalysisWorkspaceView,
    meta: { ticker: string; name: string },
  ) => void;
}) {
  if (loading) return <ResearchChatLoading />;
  return <ResearchChatShell view={view} loading={loading} symbol={symbol} onSymbolChange={onSymbolChange} onResearch={onResearch} onRefresh={onRefresh} />;
}

export default AnalysisWorkspace;

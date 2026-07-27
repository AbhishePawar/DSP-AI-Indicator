import { EmptyState } from "@/components/ui/EmptyState";

/** Consistent empty-state copy across terminal workspaces. */

export function NoSearchResultsEmpty() {
  return (
    <EmptyState
      title="No results found"
      description="Try another search term or clear filters."
    />
  );
}

export function NoResearchSessionEmpty({
  onRunAnalysis,
}: {
  onRunAnalysis?: () => void;
}) {
  return (
    <EmptyState
      title="No research session"
      description="Run an analysis first. Copilot and research views only explain fields already returned by the API."
      actionLabel={onRunAnalysis ? "Run analysis" : undefined}
      onAction={onRunAnalysis}
    />
  );
}

export function NoApiDataEmpty({ label }: { label: string }) {
  return (
    <EmptyState
      title={`${label} unavailable`}
      description="This information is not currently available from the API response."
    />
  );
}

export function NoPortfolioHoldingsEmpty() {
  return (
    <EmptyState
      title="Portfolio is empty"
      description="Add companies from Research, Companies, or Screening to start tracking holdings."
    />
  );
}

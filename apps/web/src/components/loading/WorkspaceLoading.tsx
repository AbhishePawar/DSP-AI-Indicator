import { Spinner } from "@/components/ui/Spinner";

export type WorkspaceLoadingProps = {
  label?: string;
  description?: string;
  module?: string;
};

export function WorkspaceLoading({
  label = "Loading…",
  description,
  module,
}: WorkspaceLoadingProps) {
  return (
    <div
      className="flex min-h-[12rem] flex-col items-center justify-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-6 py-10 text-center"
      role="status"
      aria-live="polite"
      aria-label={module ? `Loading ${module}` : label}
    >
      <Spinner label={label} />
      {description ? (
        <p className="max-w-sm text-sm text-[var(--muted)]">{description}</p>
      ) : null}
    </div>
  );
}

export function AnalysisLoading() {
  return (
    <WorkspaceLoading
      module="Analysis"
      label="Loading analysis workspace…"
      description="Preparing pipeline stages and recent analyses."
    />
  );
}

export function ResearchLoading() {
  return (
    <WorkspaceLoading
      module="Research"
      label="Loading research…"
      description="Fetching or restoring the research session for this company."
    />
  );
}

export function CompaniesLoading() {
  return (
    <WorkspaceLoading
      module="Company Directory"
      label="Loading company directory…"
      description="Preparing the catalogue and search index."
    />
  );
}

export function ScreeningLoading() {
  return (
    <WorkspaceLoading
      module="Screening"
      label="Loading screening workspace…"
      description="Preparing filters and catalogue data."
    />
  );
}

export function PortfolioLoading() {
  return (
    <WorkspaceLoading
      module="Portfolio"
      label="Loading portfolio…"
      description="Preparing holdings and analytics panels."
    />
  );
}

export function CopilotLoading() {
  return (
    <WorkspaceLoading
      module="Copilot"
      label="Loading copilot…"
      description="Restoring research context for explainability."
    />
  );
}

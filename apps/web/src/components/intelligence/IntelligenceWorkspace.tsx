"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { AnalysisForm } from "@/components/intelligence/AnalysisForm";
import { CapabilitiesPanel } from "@/components/intelligence/CapabilitiesPanel";
import {
  BusinessQualityCard,
  CommitteeConsensusCard,
  RecommendationCard,
} from "@/components/intelligence/DecisionCards";
import {
  EvidencePanel,
  ExecutionMetadataPanel,
  MetricsPanel,
} from "@/components/intelligence/EvidencePanels";
import { HealthIndicator } from "@/components/intelligence/HealthIndicator";
import { PipelineTimeline } from "@/components/intelligence/PipelineTimeline";
import { ValidationBanner } from "@/components/intelligence/ValidationBanner";
import { VersionCard } from "@/components/intelligence/VersionCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { api } from "@/lib/api/client";
import type { AnalyseRequest } from "@/lib/api/compositionTypes";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  emptyIntelligenceView,
  mapAnalyseResponse,
} from "@/lib/intelligence/mapResponse";

export function IntelligenceWorkspace() {
  const { session } = useAuth();
  const token = session?.accessToken;
  const [lastRequest, setLastRequest] = useState<AnalyseRequest | null>(null);

  const healthQuery = useQuery({
    queryKey: ["intelligence", "health"],
    queryFn: () => api.health({ token }),
    retry: 1,
  });

  const versionQuery = useQuery({
    queryKey: ["intelligence", "version"],
    queryFn: () => api.version({ token }),
    retry: 1,
  });

  const capabilitiesQuery = useQuery({
    queryKey: ["intelligence", "capabilities"],
    queryFn: () => api.capabilities({ token }),
    retry: 1,
  });

  const validateMutation = useMutation({
    mutationFn: (body: AnalyseRequest) =>
      api.validateAnalyse(body, { token }),
  });

  const analyseMutation = useMutation({
    mutationFn: (body: AnalyseRequest) => api.analyse(body, { token }),
  });

  const view = useMemo(() => {
    if (analyseMutation.data) return mapAnalyseResponse(analyseMutation.data);
    return emptyIntelligenceView();
  }, [analyseMutation.data]);

  const apiError =
    analyseMutation.error instanceof ApiClientError
      ? analyseMutation.error.message
      : validateMutation.error instanceof ApiClientError
        ? validateMutation.error.message
        : analyseMutation.error
          ? "Analyse failed"
          : validateMutation.error
            ? "Validation request failed"
            : null;

  const correlationId =
    (analyseMutation.error instanceof ApiClientError &&
      analyseMutation.error.body?.correlation_id) ||
    (validateMutation.error instanceof ApiClientError &&
      validateMutation.error.body?.correlation_id) ||
    analyseMutation.data?.correlation_id ||
    null;

  const validationErrors =
    (validateMutation.error instanceof ApiClientError &&
      validateMutation.error.body?.validation_errors) ||
    (analyseMutation.error instanceof ApiClientError &&
      analyseMutation.error.body?.validation_errors) ||
    validateMutation.data?.errors ||
    [];

  function runValidate(body: AnalyseRequest) {
    setLastRequest(body);
    analyseMutation.reset();
    validateMutation.mutate(body);
  }

  function runAnalyse(body: AnalyseRequest) {
    setLastRequest(body);
    validateMutation.reset();
    analyseMutation.mutate(body);
  }

  function retry() {
    if (!lastRequest) return;
    if (analyseMutation.error) {
      analyseMutation.mutate(lastRequest);
      return;
    }
    validateMutation.mutate(lastRequest);
  }

  const busy = validateMutation.isPending || analyseMutation.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Intelligence Workspace"
        description="Presentation layer over /api/v1 composition endpoints. Validate, analyse, and inspect PipelineResult summaries — no local scoring."
        actions={
          <HealthIndicator
            ready={healthQuery.data?.ready}
            status={healthQuery.data?.status}
            platformVersion={
              healthQuery.data?.platform_version ??
              versionQuery.data?.platform_version
            }
            pipelineVersion={
              healthQuery.data?.pipeline_version ??
              versionQuery.data?.pipeline_version
            }
            loading={healthQuery.isLoading}
            error={
              healthQuery.isError ? "Health check failed" : null
            }
          />
        }
      />

      <AnalysisForm
        busy={busy}
        onValidate={runValidate}
        onAnalyse={runAnalyse}
      />

      <section aria-label="Validation panel">
        <ValidationBanner
          valid={validateMutation.data?.valid ?? null}
          errors={
            validationErrors.length
              ? validationErrors
              : validateMutation.data?.errors
          }
          warnings={validateMutation.data?.warnings}
          apiError={apiError}
          correlationId={correlationId}
          onRetry={lastRequest ? retry : undefined}
        />
      </section>

      {view.warnings.length ? (
        <Alert tone="warning" title="Pipeline warnings">
          <ul className="list-inside list-disc">
            {view.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </Alert>
      ) : null}

      {view.errors.length && view.ok === false ? (
        <Alert tone="danger" title="Pipeline errors">
          <ul className="list-inside list-disc">
            {view.errors.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
          {view.correlationId ? (
            <p className="mt-2 font-mono text-xs">
              Correlation ID: {view.correlationId}
            </p>
          ) : null}
        </Alert>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <RecommendationCard
          decision={view.recommendation}
          confidence={view.recommendationConfidence}
          marginOfSafety={view.marginOfSafety}
        />
        <BusinessQualityCard
          label={view.businessQualityLabel}
          score={view.businessQualityScore}
          confidence={view.businessQualityConfidence}
        />
      </div>

      <CommitteeConsensusCard
        decision={view.committeeDecision}
        confidence={view.committeeConfidence}
        consensus={view.committeeConsensus}
        minorityNotes={view.minorityNotes}
      />

      <PipelineTimeline stages={view.stages} />

      <MetricsPanel
        strengths={view.strengths}
        weaknesses={view.weaknesses}
        risks={view.risks}
      />

      <EvidencePanel
        evidenceCounts={view.evidenceCounts}
        confidenceSummary={view.confidenceSummary}
      />

      <ExecutionMetadataPanel
        totalElapsedMs={view.totalElapsedMs}
        failedStage={view.failedStage}
        packageVersions={view.packageVersions}
        executionOrder={view.executionOrder}
        limitations={view.limitations}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <VersionCard
          apiVersion={versionQuery.data?.api_version}
          apiPackageVersion={versionQuery.data?.api_package_version}
          platformVersion={versionQuery.data?.platform_version}
          pipelineVersion={versionQuery.data?.pipeline_version}
          docsVersion={versionQuery.data?.docs_version}
        />
        <CapabilitiesPanel
          modules={capabilitiesQuery.data?.analytical_modules}
          stages={capabilitiesQuery.data?.pipeline_stages}
          reports={capabilitiesQuery.data?.supported_reports}
          platformCapabilities={capabilitiesQuery.data?.platform_capabilities}
        />
      </div>
    </div>
  );
}

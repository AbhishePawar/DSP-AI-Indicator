"use client";

import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type {
  CopilotResearchContext,
  ResearchCitationId,
} from "@/lib/copilot/types";
import { ResearchCitationList } from "./ResearchCitationList";

export function ResearchContextPanel({
  context,
  latestAnswer,
  latestCitations,
  onCompare,
}: {
  context: CopilotResearchContext;
  latestAnswer: string | null;
  latestCitations?: ResearchCitationId[];
  onCompare?: () => void;
}) {
  const ticker = context.ticker?.trim() || null;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title="Answer"
          description="Latest deterministic response"
        />
        <CardBody>
          {latestAnswer ? (
            <>
              <p className="whitespace-pre-wrap text-sm">{latestAnswer}</p>
              <ResearchCitationList
                citations={latestCitations}
                ticker={context.ticker}
              />
            </>
          ) : (
            <p className="text-sm text-[var(--muted)]">
              Ask a suggested question to see an explainability answer here.
            </p>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Related Research"
          description={
            context.hasSession
              ? `${context.company ?? ticker} · ${context.exchange ?? "—"}`
              : "No research session loaded"
          }
        />
        <CardBody className="flex flex-wrap gap-2">
          {ticker ? (
            <Link href={`/research/${encodeURIComponent(ticker)}`}>
              <Button size="sm" variant="secondary">
                Open Research
              </Button>
            </Link>
          ) : (
            <Button size="sm" variant="secondary" disabled>
              Open Research
            </Button>
          )}
          <Link href="/portfolio">
            <Button size="sm" variant="secondary">
              Open Portfolio
            </Button>
          </Link>
          <Link href={ticker ? `/analysis?symbol=${encodeURIComponent(ticker)}` : "/analysis"}>
            <Button size="sm" variant="secondary">
              Run New Analysis
            </Button>
          </Link>
          {context.canCompare ? (
            <Button
              size="sm"
              variant="secondary"
              type="button"
              onClick={onCompare}
            >
              Compare Companies
            </Button>
          ) : null}
        </CardBody>
      </Card>
    </div>
  );
}

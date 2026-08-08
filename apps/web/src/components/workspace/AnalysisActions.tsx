"use client";

import Link from "next/link";

import { AddToPortfolioButton } from "@/components/portfolio/AddToPortfolioButton";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";

export function AnalysisActions({
  ticker,
  company,
  sector,
  recommendation,
  hasResult,
  onAnalyseAnother,
  onSaveAnalysis,
  canSave,
}: {
  ticker: string;
  company: string;
  sector: string;
  recommendation?: string;
  hasResult: boolean;
  onAnalyseAnother: () => void;
  onSaveAnalysis?: () => void;
  canSave?: boolean;
}) {
  return (
    <Card>
      <CardHeader title="Quick Actions" />
      <CardBody className="flex flex-wrap gap-2">
        {ticker.trim() ? (
          <Link href={`/research/${encodeURIComponent(ticker.trim().toUpperCase())}`}>
            <Button variant="secondary" size="sm">
              Open Research
            </Button>
          </Link>
        ) : (
          <Button variant="secondary" size="sm" disabled>
            Open Research
          </Button>
        )}
        {ticker.trim() ? (
          <AddToPortfolioButton
            company={company || ticker}
            ticker={ticker.trim().toUpperCase()}
            sector={sector || "Unknown"}
            recommendation={recommendation}
            researchAvailable={hasResult}
          />
        ) : null}
        {onSaveAnalysis ? (
          <Button
            variant="secondary"
            size="sm"
            disabled={!hasResult || !canSave}
            onClick={onSaveAnalysis}
          >
            Save Analysis
          </Button>
        ) : null}
        <Button variant="ghost" size="sm" onClick={onAnalyseAnother}>
          Analyse Another Company
        </Button>
      </CardBody>
    </Card>
  );
}

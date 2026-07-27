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
        <Link href={`/research/${encodeURIComponent(ticker || "ACM")}`}>
          <Button variant="secondary" size="sm" disabled={!ticker}>
            Open Research
          </Button>
        </Link>
        <AddToPortfolioButton
          company={company || ticker || "Company"}
          ticker={ticker || "ACM"}
          sector={sector || "Unknown"}
          recommendation={recommendation}
          researchAvailable={hasResult}
        />
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

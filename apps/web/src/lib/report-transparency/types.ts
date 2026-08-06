/**
 * P2.1 — Report Transparency types (presentation only).
 */

export type DataFreshnessLabel = "Latest Available" | "Delayed" | "Unavailable";

export type QualityBadge = {
  id: string;
  label: string;
};

export type ReportTransparencyView = {
  kind: "report_transparency";
  analysisDate: string;
  analysisVersions: {
    frontend: string;
    backend: string;
    buffettFramework: string;
    institutionalRatingFramework: string;
  };
  reportId: string;
  company: {
    name: string;
    exchange: string;
    symbol: string;
  };
  dataInformation: {
    primaryDataSource: string;
    financialPeriodUsed: string;
    latestAvailableDataDate: string;
    dataFreshness: DataFreshnessLabel;
  };
  confidence: string;
  transparency: {
    analysisType: string;
    methodology: string;
    pipelineVersion: string;
    recommendationEngineVersion: string;
  };
  qualityBadges: QualityBadge[];
  disclaimer: string;
};

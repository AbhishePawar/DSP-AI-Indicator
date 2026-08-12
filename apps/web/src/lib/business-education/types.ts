/** Educational Business & Buffett Analysis — presentation types only. */

export type ClaimKind =
  | "FACT"
  | "CALCULATED_METRIC"
  | "INTERPRETATION"
  | "MANAGEMENT_CLAIM"
  | "UNAVAILABLE";

export type BusinessEducationClaim = {
  text: string;
  kind: ClaimKind;
  source: string | null;
  available: boolean;
};

export type BuffettChecklistItem = {
  id: string;
  title: string;
  evidence: string;
  strengthOrWeakness: string;
  uncertainty: string;
  source: string;
};

export type KeyRiskItem = {
  risk: string;
  whyItMatters: string;
  potentialTrigger: string;
  metricToMonitor: string;
  kind: ClaimKind;
  source: string;
};

export type BusinessEducationSectionView = {
  id: string;
  title: string;
  summary: string;
  claims: BusinessEducationClaim[];
  bullets: string[];
  checklist?: BuffettChecklistItem[];
  risks?: KeyRiskItem[];
  preferredMetrics?: string[];
  businessType?: string;
};

export type BusinessEducationReportView = {
  title: string;
  disclaimer: string;
  symbol: string;
  company: string;
  exchange: string;
  businessType: string;
  preferredMetrics: string[];
  sections: BusinessEducationSectionView[];
  readOnly: true;
  writesValuation: false;
  writesBuffettScore: false;
};

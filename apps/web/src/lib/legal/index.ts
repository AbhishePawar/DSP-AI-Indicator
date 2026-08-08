export {
  LEGAL_DOC_VERSION,
  LEGAL_EFFECTIVE_DATE,
  LEGAL_DOCUMENTS,
  LEGAL_ROUTES,
  DISCLAIMER_ACK_BULLETS,
  privacyPolicySections,
  termsOfServiceSections,
  investmentResearchDisclaimerSections,
  riskDisclosureSections,
  cookiePolicySections,
  dataUsagePolicySections,
  type LegalDocumentId,
  type LegalSection,
} from "./content";

export {
  RESEARCH_DISCLAIMER_ACK_KEY,
  isResearchDisclaimerAcknowledged,
  acknowledgeResearchDisclaimer,
  clearResearchDisclaimerAcknowledgement,
} from "./acknowledgement";

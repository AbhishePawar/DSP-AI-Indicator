import { redirect } from "next/navigation";

/**
 * Legacy pre-Figma company research route. The Figma Make `CompanyAnalysis`
 * workspace at `/analysis` is the only canonical company view, so deep links
 * (copilot citations, saved analyses, older bookmarks) are forwarded there.
 * No analysis is rendered here.
 */
export default async function CompanyResearchRoute({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;
  const symbol = decodeURIComponent(ticker).trim().toUpperCase();
  redirect(symbol ? `/analysis?symbol=${encodeURIComponent(symbol)}` : "/analysis");
}

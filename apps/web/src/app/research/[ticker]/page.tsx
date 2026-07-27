import { CompanyResearchPage } from "@/components/research/CompanyResearchPage";

export default async function CompanyResearchRoute({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;
  return <CompanyResearchPage ticker={decodeURIComponent(ticker)} />;
}

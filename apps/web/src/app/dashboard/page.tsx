"use client";

import {
  AiCopilotCardWidget,
  CompanySearchWidget,
  FavoritesWidget,
  PlatformHealthWidget,
  PlatformInfoWidget,
  QuickActionsWidget,
  RecentActivityWidget,
  RecentReportsWidget,
} from "@/components/widgets";
import { PageHeader } from "@/components/layout/PageHeader";
import { WidgetGrid } from "@/components/layout/ContentArea";
import { ResearchModeBanner } from "@/components/research/ResearchModeBanner";
import { PRODUCT } from "@/lib/product";

export default function DashboardPage() {
  return (
    <div>
      <PageHeader
        title="Dashboard"
        description={`${PRODUCT.primaryTagline} ${PRODUCT.secondaryTagline} All intelligence comes from the frozen backend APIs.`}
      />
      <div className="mb-6">
        <ResearchModeBanner />
      </div>
      <WidgetGrid>
        <QuickActionsWidget />
        <PlatformHealthWidget />
        <PlatformInfoWidget />
        <CompanySearchWidget />
        <AiCopilotCardWidget />
        <FavoritesWidget />
        <RecentReportsWidget />
        <RecentActivityWidget />
      </WidgetGrid>
    </div>
  );
}

"use client";

import { cn } from "@/lib/utils";
import { PlatformHealthWidget } from "./widgets/SystemAiWidgets";
import { RecentlyViewedCompaniesWidget, PinnedCompaniesWidget } from "./widgets/CompanyWidgets";
import { QuickActionsWidget } from "./widgets/QuickActionsWidget";
import { ResearchCommandCenterWidget } from "./widgets/ResearchCommandCenterWidget";
import { WelcomeWidget } from "./widgets/WelcomeWidget";

export function DashboardGrid() {
  return (
    <div className="mx-auto mt-8 max-w-6xl grid gap-4 sm:grid-cols-2">
      <div className={cn("sm:col-span-2")}>
        <WelcomeWidget />
      </div>
      <div className={cn("sm:col-span-2")}>
        <QuickActionsWidget />
      </div>
      <div className={cn("sm:col-span-2")}>
        <ResearchCommandCenterWidget />
      </div>
      <PlatformHealthWidget />
      <RecentlyViewedCompaniesWidget />
      <PinnedCompaniesWidget />
    </div>
  );
}

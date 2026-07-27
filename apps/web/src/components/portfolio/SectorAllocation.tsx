"use client";

import type { AllocationSegment } from "@/lib/portfolio/model";
import { AllocationCard } from "./AllocationCard";

export function SectorAllocation({
  segments,
}: {
  segments: AllocationSegment[];
}) {
  return (
    <AllocationCard
      title="Sector Allocation"
      segments={segments}
      description="Technology · Financials · Consumer · Healthcare · Industrials · Others"
    />
  );
}

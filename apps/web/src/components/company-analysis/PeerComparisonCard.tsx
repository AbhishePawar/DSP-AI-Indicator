"use client";

import React from "react";
import { Badge } from "@/components/ds/data/badge";
import { cn } from "@/lib/utils";

export type PeerEligibilityType = "DIRECT_PEER" | "RELATED_PEER" | "NOT_COMPARABLE";

export interface PeerItem {
  symbol: string;
  name: string;
  eligibility: PeerEligibilityType;
  rationale: string;
  operatingMargin?: number | null;
  roe?: number | null;
  roce?: number | null;
  debtToEquity?: number | null;
  revenueGrowth?: number | null;
  peRatio?: number | null;
}

export interface PeerComparisonCardProps {
  primarySymbol: string;
  primaryName?: string;
  primaryMetrics: {
    operatingMargin?: number | null;
    roe?: number | null;
    roce?: number | null;
    debtToEquity?: number | null;
    revenueGrowth?: number | null;
    peRatio?: number | null;
  };
  p109State?: "COMPLETE" | "PARTIAL_DATA" | "INSUFFICIENT_DATA" | "SYSTEM_ERROR";
  peers?: PeerItem[];
  className?: string;
}

function formatPercent(val?: number | null): string {
  if (val === undefined || val === null || isNaN(val)) {
    return "Data unavailable";
  }
  return `${(val * 100).toFixed(1)}%`;
}

function formatRatio(val?: number | null): string {
  if (val === undefined || val === null || isNaN(val)) {
    return "Data unavailable";
  }
  return `${val.toFixed(2)}x`;
}

export function PeerComparisonCard({
  primarySymbol,
  primaryName,
  primaryMetrics,
  p109State = "COMPLETE",
  peers = [],
  className,
}: PeerComparisonCardProps) {
  // Allow valuation only under COMPLETE P1-09 state
  const allowValuation = p109State === "COMPLETE";

  return (
    <div
      className={cn(
        "rounded-xl border border-border/70 bg-card/60 p-5 shadow-xs backdrop-blur-xs transition-all",
        className
      )}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/50 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              Peer & Competitor Intelligence
            </span>
            <Badge variant="outline" className="text-[10px] uppercase font-mono py-0 h-5">
              Deterministic Verification
            </Badge>
          </div>
          <h3 className="text-base font-semibold text-foreground mt-0.5">
            {primarySymbol} vs Verified Peers
          </h3>
        </div>
        <p className="text-xs text-muted-foreground max-w-sm">
          Deterministic peer discovery via registered industry taxonomy and strict eligibility policy.
        </p>
      </div>

      {peers.length === 0 ? (
        <div className="py-8 text-center text-sm text-muted-foreground">
          No verified peers registered for {primarySymbol} under current deterministic industry policy.
        </div>
      ) : (
        <div className="mt-4 space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse min-w-[540px]">
              <thead>
                <tr className="border-b border-border/60 text-muted-foreground">
                  <th className="py-2.5 px-3 font-medium">Metric</th>
                  <th className="py-2.5 px-3 font-semibold text-foreground bg-muted/30 rounded-t-md">
                    {primarySymbol} (Primary)
                  </th>
                  {peers.map((peer) => (
                    <th key={peer.symbol} className="py-2.5 px-3 font-medium">
                      <div className="flex items-center gap-1.5">
                        <span>{peer.symbol}</span>
                        <span
                          className={cn(
                            "text-[9px] px-1.5 py-0.5 rounded font-mono font-medium",
                            peer.eligibility === "DIRECT_PEER"
                              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                              : "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                          )}
                        >
                          {peer.eligibility === "DIRECT_PEER" ? "DIRECT" : "RELATED"}
                        </span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                <tr>
                  <td className="py-2 px-3 font-medium text-muted-foreground">Operating Margin</td>
                  <td className="py-2 px-3 font-mono font-medium text-foreground bg-muted/20">
                    {formatPercent(primaryMetrics.operatingMargin)}
                  </td>
                  {peers.map((peer) => (
                    <td key={peer.symbol} className="py-2 px-3 font-mono text-muted-foreground">
                      {formatPercent(peer.operatingMargin)}
                    </td>
                  ))}
                </tr>

                <tr>
                  <td className="py-2 px-3 font-medium text-muted-foreground">Return on Equity (ROE)</td>
                  <td className="py-2 px-3 font-mono font-medium text-foreground bg-muted/20">
                    {formatPercent(primaryMetrics.roe)}
                  </td>
                  {peers.map((peer) => (
                    <td key={peer.symbol} className="py-2 px-3 font-mono text-muted-foreground">
                      {formatPercent(peer.roe)}
                    </td>
                  ))}
                </tr>

                <tr>
                  <td className="py-2 px-3 font-medium text-muted-foreground">ROCE</td>
                  <td className="py-2 px-3 font-mono font-medium text-foreground bg-muted/20">
                    {formatPercent(primaryMetrics.roce)}
                  </td>
                  {peers.map((peer) => (
                    <td key={peer.symbol} className="py-2 px-3 font-mono text-muted-foreground">
                      {formatPercent(peer.roce)}
                    </td>
                  ))}
                </tr>

                <tr>
                  <td className="py-2 px-3 font-medium text-muted-foreground">Debt / Equity</td>
                  <td className="py-2 px-3 font-mono font-medium text-foreground bg-muted/20">
                    {formatRatio(primaryMetrics.debtToEquity)}
                  </td>
                  {peers.map((peer) => (
                    <td key={peer.symbol} className="py-2 px-3 font-mono text-muted-foreground">
                      {formatRatio(peer.debtToEquity)}
                    </td>
                  ))}
                </tr>

                <tr>
                  <td className="py-2 px-3 font-medium text-muted-foreground">Revenue Growth</td>
                  <td className="py-2 px-3 font-mono font-medium text-foreground bg-muted/20">
                    {formatPercent(primaryMetrics.revenueGrowth)}
                  </td>
                  {peers.map((peer) => (
                    <td key={peer.symbol} className="py-2 px-3 font-mono text-muted-foreground">
                      {formatPercent(peer.revenueGrowth)}
                    </td>
                  ))}
                </tr>

                <tr>
                  <td className="py-2 px-3 font-medium text-muted-foreground">
                    Valuation P/E Multiple
                  </td>
                  <td className="py-2 px-3 font-mono font-medium text-foreground bg-muted/20">
                    {allowValuation ? formatRatio(primaryMetrics.peRatio) : "Unavailable — valuation data incomplete"}
                  </td>
                  {peers.map((peer) => (
                    <td key={peer.symbol} className="py-2 px-3 font-mono text-muted-foreground">
                      {allowValuation ? formatRatio(peer.peRatio) : "Unavailable — valuation data incomplete"}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>

          <div className="rounded-lg bg-muted/40 p-3 text-[11px] text-muted-foreground space-y-1.5">
            <p className="font-semibold text-foreground">Why these peers?</p>
            <ul className="space-y-1 list-disc list-inside">
              {peers.map((peer) => (
                <li key={peer.symbol}>
                  <span className="font-medium text-foreground">{peer.name || peer.symbol} ({peer.symbol}):</span>{" "}
                  {peer.rationale || "Eligible industry peer under deterministic taxonomy."}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

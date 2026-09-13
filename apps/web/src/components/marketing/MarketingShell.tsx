"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { MarketingFooter } from "./MarketingFooter";
import { MarketingHeader } from "./MarketingHeader";
import "./marketing.css";

export function MarketingShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isWorkspaceHome = pathname === "/";

  return (
    <div className="flex min-h-screen flex-col bg-[var(--bg)] text-[var(--fg)]">
      {!isWorkspaceHome ? <MarketingHeader /> : null}
      <div className="flex-1">{children}</div>
      {!isWorkspaceHome ? <MarketingFooter /> : null}
    </div>
  );
}

"use client";

import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Spinner } from "./spinner";

export type LoadingOverlayProps = HTMLAttributes<HTMLDivElement> & {
  visible?: boolean;
  label?: string;
  children?: ReactNode;
};

export function LoadingOverlay({
  visible = true,
  label = "Loading",
  className,
  children,
  ...props
}: LoadingOverlayProps) {
  if (!visible) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className={cn(
        "absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 bg-[color-mix(in_srgb,var(--bg)_72%,transparent)] backdrop-blur-[1px] motion-reduce:backdrop-blur-none",
        className,
      )}
      {...props}
    >
      <Spinner label={label} size="lg" />
      <span className="text-sm text-[var(--muted)]">{label}</span>
      {children}
    </div>
  );
}

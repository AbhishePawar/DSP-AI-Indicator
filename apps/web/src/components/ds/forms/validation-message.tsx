"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface ValidationMessageProps extends React.HTMLAttributes<HTMLParagraphElement> {
  tone?: "error" | "warning";
}

const ValidationMessage = React.forwardRef<HTMLParagraphElement, ValidationMessageProps>(
  ({ className, tone = "error", children, role = "alert", ...props }, ref) => {
    if (!children) return null;

    return (
      <p
        ref={ref}
        role={role}
        className={cn(
          "text-xs font-medium",
          tone === "error" && "text-[var(--danger-fg)]",
          tone === "warning" && "text-[var(--warning-fg,#7a5a12)]",
          className,
        )}
        {...props}
      >
        {children}
      </p>
    );
  },
);
ValidationMessage.displayName = "ValidationMessage";

export { ValidationMessage };

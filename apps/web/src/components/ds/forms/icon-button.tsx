"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Button, type ButtonProps } from "./button";

export interface IconButtonProps extends Omit<ButtonProps, "children" | "aria-label"> {
  /** Accessible name — required for icon-only controls. */
  "aria-label": string;
  children: React.ReactNode;
}

const sizeSquare: Record<NonNullable<ButtonProps["size"]>, string> = {
  sm: "h-9 w-9 min-h-9 min-w-9 p-0",
  md: "h-11 w-11 min-h-11 min-w-11 p-0",
  lg: "h-12 w-12 min-h-12 min-w-12 p-0",
};

const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ className, size = "md", children, ...props }, ref) => {
    return (
      <Button
        ref={ref}
        size={size}
        className={cn(sizeSquare[size ?? "md"], "shrink-0", className)}
        {...props}
      >
        {children}
      </Button>
    );
  },
);
IconButton.displayName = "IconButton";

export { IconButton };

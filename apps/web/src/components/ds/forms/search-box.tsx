"use client";

import * as React from "react";
import { Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input, type InputProps } from "./input";

export interface SearchBoxProps extends Omit<InputProps, "type"> {
  /** Accessible label for the search field. */
  "aria-label"?: string;
}

const SearchBox = React.forwardRef<HTMLInputElement, SearchBoxProps>(
  ({ className, "aria-label": ariaLabel = "Search", ...props }, ref) => {
    return (
      <div className="relative w-full">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted)]"
          aria-hidden
        />
        <Input
          ref={ref}
          type="search"
          role="searchbox"
          aria-label={ariaLabel}
          className={cn("pl-9", className)}
          {...props}
        />
      </div>
    );
  },
);
SearchBox.displayName = "SearchBox";

export { SearchBox };

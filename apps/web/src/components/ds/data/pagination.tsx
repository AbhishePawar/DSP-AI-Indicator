"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "../forms/button";

export interface PaginationProps extends React.HTMLAttributes<HTMLElement> {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  /** Inclusive sibling window around current page. */
  siblingCount?: number;
}

function range(start: number, end: number) {
  const length = end - start + 1;
  return Array.from({ length }, (_, i) => start + i);
}

function Pagination({
  page,
  pageCount,
  onPageChange,
  siblingCount = 1,
  className,
  ...props
}: PaginationProps) {
  const safePage = Math.min(Math.max(page, 1), Math.max(pageCount, 1));
  const safeCount = Math.max(pageCount, 1);

  const pages = React.useMemo(() => {
    const totalNumbers = siblingCount * 2 + 3;
    if (safeCount <= totalNumbers) {
      return range(1, safeCount);
    }
    const left = Math.max(safePage - siblingCount, 1);
    const right = Math.min(safePage + siblingCount, safeCount);
    const showLeftEllipsis = left > 2;
    const showRightEllipsis = right < safeCount - 1;
    const items: Array<number | "ellipsis"> = [1];
    if (showLeftEllipsis) items.push("ellipsis");
    items.push(...range(left === 1 ? 2 : left, right === safeCount ? safeCount - 1 : right));
    if (showRightEllipsis) items.push("ellipsis");
    if (safeCount > 1) items.push(safeCount);
    return items;
  }, [safePage, safeCount, siblingCount]);

  return (
    <nav
      aria-label="Pagination"
      className={cn("flex items-center gap-1", className)}
      {...props}
    >
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-label="Previous page"
        disabled={safePage <= 1}
        onClick={() => onPageChange(safePage - 1)}
      >
        <ChevronLeft className="h-4 w-4" aria-hidden />
      </Button>
      {pages.map((item, index) =>
        item === "ellipsis" ? (
          <span
            key={`e-${index}`}
            className="px-2 text-sm text-[var(--muted)]"
            aria-hidden
          >
            …
          </span>
        ) : (
          <Button
            key={item}
            type="button"
            variant={item === safePage ? "primary" : "ghost"}
            size="sm"
            aria-label={`Page ${item}`}
            aria-current={item === safePage ? "page" : undefined}
            onClick={() => onPageChange(item)}
          >
            {item}
          </Button>
        ),
      )}
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-label="Next page"
        disabled={safePage >= safeCount}
        onClick={() => onPageChange(safePage + 1)}
      >
        <ChevronRight className="h-4 w-4" aria-hidden />
      </Button>
    </nav>
  );
}

export { Pagination };

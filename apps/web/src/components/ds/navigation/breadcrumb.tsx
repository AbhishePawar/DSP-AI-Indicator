import type { AnchorHTMLAttributes, HTMLAttributes, ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export type BreadcrumbProps = HTMLAttributes<HTMLElement>;

export function Breadcrumb({ className, children, ...props }: BreadcrumbProps) {
  return (
    <nav aria-label="Breadcrumb" className={cn("text-sm", className)} {...props}>
      <ol className="flex flex-wrap items-center gap-1 text-[var(--muted)]">
        {children}
      </ol>
    </nav>
  );
}

export type BreadcrumbItemProps = AnchorHTMLAttributes<HTMLAnchorElement> & {
  current?: boolean;
  children: ReactNode;
};

export function BreadcrumbItem({
  current = false,
  className,
  children,
  href,
  ...props
}: BreadcrumbItemProps) {
  if (current || !href) {
    return (
      <li
        className={cn(
          "inline-flex items-center text-[var(--fg)]",
          current && "font-medium",
          className,
        )}
        aria-current={current ? "page" : undefined}
      >
        <span>{children}</span>
      </li>
    );
  }

  return (
    <li className={cn("inline-flex items-center", className)}>
      <a
        href={href}
        className="rounded-sm text-[var(--muted)] transition hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        {...props}
      >
        {children}
      </a>
    </li>
  );
}

export type BreadcrumbSeparatorProps = HTMLAttributes<HTMLLIElement>;

export function BreadcrumbSeparator({
  className,
  children,
  ...props
}: BreadcrumbSeparatorProps) {
  return (
    <li
      role="presentation"
      aria-hidden
      className={cn("inline-flex items-center text-[var(--muted)]", className)}
      {...props}
    >
      {children ?? <ChevronRight className="size-3.5" />}
    </li>
  );
}

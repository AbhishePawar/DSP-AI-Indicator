import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Container, type ContainerSize } from "./container";

export type PageLayoutProps = HTMLAttributes<HTMLDivElement> & {
  title: string;
  description?: string;
  actions?: ReactNode;
  size?: ContainerSize;
};

export function PageLayout({
  title,
  description,
  actions,
  size = "xl",
  className,
  children,
  ...props
}: PageLayoutProps) {
  return (
    <div
      className={cn("min-h-full bg-[var(--bg)] text-[var(--fg)]", className)}
      {...props}
    >
      <Container size={size} className="py-6 sm:py-8">
        <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h1 className="font-[family-name:var(--font-display)] text-2xl tracking-tight sm:text-3xl">
              {title}
            </h1>
            {description ? (
              <p className="mt-2 max-w-2xl text-sm text-[var(--muted)] sm:text-base">
                {description}
              </p>
            ) : null}
          </div>
          {actions ? (
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              {actions}
            </div>
          ) : null}
        </header>
        {children}
      </Container>
    </div>
  );
}

import type { ReactNode } from "react";

import { EmptyState, ErrorState, Skeleton, Spinner } from "@/components/ds";
import { cn } from "@/lib/utils";

/** Consistent page shell spacing + subtle route enter (respects reduced motion). */
export function ContentArea({ children }: { children: ReactNode }) {
  return (
    <div className="dsp-page-enter mx-auto w-full max-w-6xl space-y-6 px-4 py-6 sm:space-y-8 sm:px-6 sm:py-8">
      {children}
    </div>
  );
}

/** F003 page container — main scroll region content wrapper. */
export function PageContainer({
  children,
  className,
  narrow = false,
}: {
  children: ReactNode;
  className?: string;
  narrow?: boolean;
}) {
  return (
    <div
      className={cn(
        "dsp-page-enter mx-auto w-full space-y-6 px-4 py-6 sm:space-y-8 sm:px-6 sm:py-8",
        narrow ? "max-w-3xl" : "max-w-6xl",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function WidgetGrid({ children }: { children: ReactNode }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{children}</div>
  );
}

/** Section rhythm used across Dashboard → Beta workspaces. */
export function SectionStack({ children }: { children: ReactNode }) {
  return <div className="space-y-4 sm:space-y-5">{children}</div>;
}

export function LoadingLayout({
  label = "Loading…",
  description,
}: {
  label?: string;
  description?: string;
}) {
  return (
    <PageContainer>
      <div
        className="flex min-h-[16rem] flex-col items-center justify-center gap-4"
        role="status"
        aria-live="polite"
        aria-label={label}
      >
        <Spinner />
        <p className="text-sm text-[var(--fg)]">{label}</p>
        {description ? (
          <p className="max-w-sm text-center text-sm text-[var(--muted)]">
            {description}
          </p>
        ) : null}
        <div className="mt-4 grid w-full max-w-md gap-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-3/4" />
          <Skeleton className="h-24 w-full" />
        </div>
      </div>
    </PageContainer>
  );
}

export function ErrorLayout({
  title = "Something went wrong",
  description = "Data unavailable.",
  action,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <PageContainer>
      <ErrorState title={title} description={description} action={action} />
    </PageContainer>
  );
}

export function EmptyLayout({
  title = "Data unavailable.",
  description,
  action,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <PageContainer>
      <EmptyState title={title} description={description} action={action} />
    </PageContainer>
  );
}

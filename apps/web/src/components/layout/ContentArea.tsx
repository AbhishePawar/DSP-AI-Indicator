import type { ReactNode } from "react";

/** Consistent page shell spacing + subtle route enter (respects reduced motion). */
export function ContentArea({ children }: { children: ReactNode }) {
  return (
    <div className="dsp-page-enter mx-auto w-full max-w-6xl space-y-6 px-4 py-6 sm:space-y-8 sm:px-6 sm:py-8">
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

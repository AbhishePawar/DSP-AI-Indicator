import type { CSSProperties, HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

export type ResponsiveWrapperProps = HTMLAttributes<HTMLDivElement> & {
  /** CSS aspect-ratio value, e.g. "16 / 9" or "1 / 1". */
  aspect?: string;
  children: ReactNode;
};

export function ResponsiveWrapper({
  aspect = "16 / 9",
  className,
  style,
  children,
  ...props
}: ResponsiveWrapperProps) {
  return (
    <div
      className={cn("relative w-full overflow-hidden", className)}
      style={
        {
          aspectRatio: aspect,
          ...style,
        } as CSSProperties
      }
      {...props}
    >
      <div className="absolute inset-0 h-full w-full">{children}</div>
    </div>
  );
}

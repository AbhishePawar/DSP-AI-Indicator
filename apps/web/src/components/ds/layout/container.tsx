import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const maxWidthClass = {
  sm: "max-w-screen-sm",
  md: "max-w-screen-md",
  lg: "max-w-screen-lg",
  xl: "max-w-screen-xl",
  full: "max-w-none",
} as const;

export type ContainerSize = keyof typeof maxWidthClass;

export type ContainerProps = HTMLAttributes<HTMLDivElement> & {
  size?: ContainerSize;
};

export function Container({
  size = "lg",
  className,
  children,
  ...props
}: ContainerProps) {
  return (
    <div
      className={cn(
        "mx-auto w-full px-4 sm:px-6",
        maxWidthClass[size],
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

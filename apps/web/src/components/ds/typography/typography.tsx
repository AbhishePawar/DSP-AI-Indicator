import type { ElementType, HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

const variantClass = {
  display:
    "font-[family-name:var(--font-display)] text-4xl font-semibold tracking-tight sm:text-5xl",
  h1: "font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight sm:text-4xl",
  h2: "font-[family-name:var(--font-display)] text-2xl font-semibold tracking-tight",
  h3: "font-[family-name:var(--font-display)] text-xl font-semibold tracking-tight",
  h4: "font-[family-name:var(--font-display)] text-lg font-medium tracking-tight",
  h5: "font-[family-name:var(--font-body)] text-base font-medium",
  h6: "font-[family-name:var(--font-body)] text-sm font-medium uppercase tracking-wide",
  body: "font-[family-name:var(--font-body)] text-base leading-relaxed",
  caption: "font-[family-name:var(--font-body)] text-sm text-[var(--muted)]",
  mono: "font-mono text-sm tabular-nums",
} as const;

const defaultElement = {
  display: "h1",
  h1: "h1",
  h2: "h2",
  h3: "h3",
  h4: "h4",
  h5: "h5",
  h6: "h6",
  body: "p",
  caption: "p",
  mono: "code",
} as const;

export type TypographyVariant = keyof typeof variantClass;

export type TypographyProps = HTMLAttributes<HTMLElement> & {
  variant?: TypographyVariant;
  as?: ElementType;
  muted?: boolean;
  children?: ReactNode;
};

export function Typography({
  variant = "body",
  as,
  muted = false,
  className,
  children,
  ...props
}: TypographyProps) {
  const Comp = (as ?? defaultElement[variant]) as ElementType;

  return (
    <Comp
      className={cn(
        "text-[var(--fg)]",
        variantClass[variant],
        muted && "text-[var(--muted)]",
        className,
      )}
      {...props}
    >
      {children}
    </Comp>
  );
}

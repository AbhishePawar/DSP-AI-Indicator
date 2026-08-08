"use client";

import * as React from "react";
import * as LabelPrimitive from "@radix-ui/react-label";
import { cn } from "@/lib/utils";
import { ValidationMessage } from "./validation-message";

export interface FormFieldProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: React.ReactNode;
}

function FormField({
  label,
  htmlFor,
  hint,
  error,
  required,
  children,
  className,
  ...props
}: FormFieldProps) {
  const hintId = React.useId();
  const errorId = React.useId();
  const describedBy = [hint ? hintId : null, error ? errorId : null]
    .filter(Boolean)
    .join(" ") || undefined;

  return (
    <div className={cn("flex flex-col gap-1.5", className)} {...props}>
      <LabelPrimitive.Root
        htmlFor={htmlFor}
        className="text-sm font-medium text-[var(--fg)]"
      >
        {label}
        {required ? (
          <span className="ml-0.5 text-[var(--danger-fg)]" aria-hidden>
            *
          </span>
        ) : null}
        {required ? <span className="sr-only"> (required)</span> : null}
      </LabelPrimitive.Root>
      {React.isValidElement<{
        id?: string;
        "aria-invalid"?: boolean;
        "aria-describedby"?: string;
      }>(children)
        ? React.cloneElement(children, {
            id: htmlFor ?? children.props.id,
            "aria-invalid": error ? true : undefined,
            "aria-describedby": describedBy,
          })
        : children}
      {hint && !error ? (
        <p id={hintId} className="text-xs text-[var(--muted)]">
          {hint}
        </p>
      ) : null}
      {error ? <ValidationMessage id={errorId}>{error}</ValidationMessage> : null}
    </div>
  );
}

export { FormField };

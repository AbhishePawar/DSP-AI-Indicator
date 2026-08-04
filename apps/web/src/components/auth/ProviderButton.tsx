"use client";

import { Button, type ButtonProps } from "@/components/ds";
import { cn } from "@/lib/utils";
import { ProviderIcon } from "./ProviderIcons";

export type ProviderButtonProps = Omit<ButtonProps, "children"> & {
  provider: string;
  /** Human label, e.g. "Continue with Google". Falls back to a generic label. */
  label?: string;
  comingSoon?: boolean;
};

function defaultLabel(provider: string): string {
  switch (provider.toUpperCase()) {
    case "GOOGLE":
      return "Continue with Google";
    case "MICROSOFT":
      return "Continue with Microsoft";
    case "FACEBOOK":
      return "Continue with Facebook";
    default:
      return `Continue with ${provider}`;
  }
}

/**
 * Branded OAuth provider button. Renders the official mark for
 * Google / Microsoft / Facebook; unknown providers (e.g. a future generic
 * Enterprise SSO / OIDC connector reported by the backend) fall back to a
 * neutral label with no icon, so new providers "just work" without a
 * frontend code change.
 */
export function ProviderButton({
  provider,
  label,
  comingSoon,
  className,
  ...props
}: ProviderButtonProps) {
  return (
    <Button
      type="button"
      variant="secondary"
      className={cn("w-full justify-center", comingSoon && "opacity-70", className)}
      aria-label={label ?? defaultLabel(provider)}
      {...props}
    >
      <ProviderIcon provider={provider} className="shrink-0" />
      <span>
        {label ?? defaultLabel(provider)}
        {comingSoon ? " — Coming Soon" : ""}
      </span>
    </Button>
  );
}

"use client";

import { Button } from "@/components/ui/Button";

export function FilterChip({
  label,
  active = false,
  onClick,
}: {
  label: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <Button
      type="button"
      size="sm"
      variant={active ? "primary" : "secondary"}
      onClick={onClick}
      aria-pressed={active}
    >
      {label}
    </Button>
  );
}

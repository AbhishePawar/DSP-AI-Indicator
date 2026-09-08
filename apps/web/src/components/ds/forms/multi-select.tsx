"use client";

import * as React from "react";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Popover, PopoverContent, PopoverTrigger } from "../data/popover";
import { Button } from "./button";
import { Checkbox } from "./checkbox";

export interface MultiSelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface MultiSelectProps {
  options: MultiSelectOption[];
  value: string[];
  onValueChange: (value: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  "aria-label"?: string;
}

function MultiSelect({
  options,
  value,
  onValueChange,
  placeholder = "Select…",
  disabled = false,
  className,
  "aria-label": ariaLabel = "Multi select",
}: MultiSelectProps) {
  const [open, setOpen] = React.useState(false);

  const selectedLabels = options
    .filter((o) => value.includes(o.value))
    .map((o) => o.label);

  const toggle = (optionValue: string) => {
    if (value.includes(optionValue)) {
      onValueChange(value.filter((v) => v !== optionValue));
    } else {
      onValueChange([...value, optionValue]);
    }
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          aria-label={ariaLabel}
          aria-expanded={open}
          className={cn(
            "h-11 w-full justify-between font-normal",
            !selectedLabels.length && "text-[var(--muted)]",
            className,
          )}
        >
          <span className="truncate">
            {selectedLabels.length ? selectedLabels.join(", ") : placeholder}
          </span>
          <ChevronDown className="h-4 w-4 shrink-0 text-[var(--muted)]" aria-hidden />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-[var(--radix-popover-trigger-width)] p-1">
        <ul role="listbox" aria-multiselectable="true" aria-label={ariaLabel} className="max-h-60 overflow-auto">
          {options.map((option) => {
            const checked = value.includes(option.value);
            const id = `ms-${option.value}`;
            return (
              <li key={option.value} role="option" aria-selected={checked}>
                <label
                  htmlFor={id}
                  className={cn(
                    "flex cursor-pointer items-center gap-2 rounded-[calc(var(--radius-md,0.5rem)-2px)] px-2 py-2 text-sm",
                    "hover:bg-[var(--accent-soft)]",
                    option.disabled && "pointer-events-none opacity-50",
                  )}
                >
                  <Checkbox
                    id={id}
                    checked={checked}
                    disabled={option.disabled}
                    onCheckedChange={() => toggle(option.value)}
                    aria-label={option.label}
                  />
                  <span className="flex-1">{option.label}</span>
                  {checked ? (
                    <Check className="h-3.5 w-3.5 text-[var(--accent)]" aria-hidden />
                  ) : null}
                </label>
              </li>
            );
          })}
        </ul>
      </PopoverContent>
    </Popover>
  );
}

export { MultiSelect };

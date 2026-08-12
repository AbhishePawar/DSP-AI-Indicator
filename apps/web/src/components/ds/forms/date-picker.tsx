"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Input, type InputProps } from "./input";

export type DatePickerProps = Omit<InputProps, "type">;

const DatePicker = React.forwardRef<HTMLInputElement, DatePickerProps>(
  ({ className, ...props }, ref) => {
    return (
      <Input
        ref={ref}
        type="date"
        className={cn(
          "[&::-webkit-calendar-picker-indicator]:cursor-pointer",
          "[&::-webkit-calendar-picker-indicator]:opacity-70",
          className,
        )}
        {...props}
      />
    );
  },
);
DatePicker.displayName = "DatePicker";

export { DatePicker };

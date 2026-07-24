"use client";

import type { FormEvent } from "react";
import { Input } from "./Input";
import { Button } from "./Button";

export function SearchBox({
  value,
  onChange,
  onSubmit,
  placeholder = "Search…",
  label = "Search",
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  label?: string;
}) {
  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSubmit();
  }

  return (
    <form
      onSubmit={handleSubmit}
      role="search"
      className="flex gap-2"
      aria-label={label}
    >
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={label}
      />
      <Button type="submit" variant="secondary">
        Search
      </Button>
    </form>
  );
}

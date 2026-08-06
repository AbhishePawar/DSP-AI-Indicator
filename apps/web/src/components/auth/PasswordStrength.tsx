"use client";

import { evaluatePasswordStrength } from "./authValidation";

type PasswordStrengthProps = {
  password: string;
};

export function PasswordStrengthMeter({ password }: PasswordStrengthProps) {
  if (!password) return null;
  const result = evaluatePasswordStrength(password);
  const pct = (result.score / 4) * 100;

  return (
    <div className="space-y-1.5" aria-live="polite">
      <div
        className="h-1.5 overflow-hidden rounded-full bg-[var(--surface-2)]"
        role="meter"
        aria-label="Password strength"
        aria-valuemin={0}
        aria-valuemax={4}
        aria-valuenow={result.score}
        aria-valuetext={result.label}
      >
        <div
          className="h-full rounded-full bg-[var(--accent)] transition-[width] duration-[var(--motion-normal)] motion-reduce:transition-none"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-[var(--muted)]">
        Strength: <span className="text-[var(--fg)]">{result.label}</span>
        {result.hints.length > 0 ? ` — ${result.hints[0]}` : null}
      </p>
    </div>
  );
}

import { describe, expect, it } from "vitest";

import {
  evaluatePasswordStrength,
  isValidEmail,
  mapAuthError,
} from "./authValidation";

describe("authValidation", () => {
  it("validates email shapes", () => {
    expect(isValidEmail("a@b.co")).toBe(true);
    expect(isValidEmail("bad")).toBe(false);
    expect(isValidEmail("")).toBe(false);
  });

  it("scores password strength", () => {
    expect(evaluatePasswordStrength("short").score).toBeLessThan(2);
    expect(evaluatePasswordStrength("LongerPass1!").score).toBeGreaterThanOrEqual(
      2,
    );
  });

  it("maps rate-limit and credential errors", () => {
    expect(mapAuthError(new Error("429 too many"))).toMatch(/Too many attempts/i);
    expect(mapAuthError(new Error("Invalid credentials"))).toMatch(
      /not accepted/i,
    );
  });
});

import { describe, expect, it } from "vitest";

import {
  evaluatePasswordStrength,
  isPlausibleLoginIdentifier,
  isValidEmail,
  mapAuthError,
  normalizeIndiaMobileInput,
  normalizeLoginIdentifier,
} from "./authValidation";

describe("authValidation", () => {
  it("validates email shapes", () => {
    expect(isValidEmail("a@b.co")).toBe(true);
    expect(isValidEmail("bad")).toBe(false);
    expect(isValidEmail("")).toBe(false);
  });

  it("normalizes India mobile identifiers", () => {
    expect(normalizeIndiaMobileInput("9876543210")).toBe("+919876543210");
    expect(normalizeIndiaMobileInput("+91 98765-43210")).toBe("+919876543210");
    expect(normalizeIndiaMobileInput("12345")).toBeNull();
  });

  it("accepts username, email, or India mobile as login identifiers", () => {
    expect(isPlausibleLoginIdentifier("analyst")).toBe(true);
    expect(isPlausibleLoginIdentifier("a@b.co")).toBe(true);
    expect(isPlausibleLoginIdentifier("9876543210")).toBe(true);
    expect(isPlausibleLoginIdentifier("+919876543210")).toBe(true);
    expect(isPlausibleLoginIdentifier("91 98765 43210")).toBe(true);
    expect(isPlausibleLoginIdentifier("no")).toBe(false);
    expect(isPlausibleLoginIdentifier("12")).toBe(false);
    expect(normalizeLoginIdentifier("Ada@Example.COM")).toBe("ada@example.com");
    expect(normalizeLoginIdentifier("9876543210")).toBe("+919876543210");
    expect(normalizeLoginIdentifier("  Analyst_1 ")).toBe("Analyst_1");
  });

  it("scores password strength", () => {
    expect(evaluatePasswordStrength("short").score).toBeLessThan(2);
    expect(evaluatePasswordStrength("LongerPass1!").score).toBeGreaterThanOrEqual(
      2,
    );
  });

  it("maps rate-limit and credential errors to user-facing copy", () => {
    expect(mapAuthError(new Error("429 too many"))).toMatch(/Too many attempts/i);
    expect(mapAuthError(new Error("Invalid credentials"))).toMatch(
      /Unable to sign in/i,
    );
    expect(mapAuthError(new Error("POST /api/v1/auth/rbac/login failed"))).not.toMatch(
      /\/api\//i,
    );
  });
});


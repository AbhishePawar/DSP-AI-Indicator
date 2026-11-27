import { describe, it, expect } from "vitest";
import { resolvePostLoginDestination } from "./finishEnterpriseSession";

describe("resolvePostLoginDestination", () => {
  it("redirects empty or whitespace destination to /dashboard", () => {
    expect(resolvePostLoginDestination("")).toBe("/dashboard");
    expect(resolvePostLoginDestination("   ")).toBe("/dashboard");
    expect(resolvePostLoginDestination(null)).toBe("/dashboard");
    expect(resolvePostLoginDestination(undefined)).toBe("/dashboard");
  });

  it("redirects root path '/' to /dashboard", () => {
    expect(resolvePostLoginDestination("/")).toBe("/dashboard");
  });

  it("redirects public marketing routes to /dashboard", () => {
    expect(resolvePostLoginDestination("/about")).toBe("/dashboard");
    expect(resolvePostLoginDestination("/contact")).toBe("/dashboard");
    expect(resolvePostLoginDestination("/pricing")).toBe("/dashboard");
    expect(resolvePostLoginDestination("/faq")).toBe("/dashboard");
  });

  it("preserves /dashboard", () => {
    expect(resolvePostLoginDestination("/dashboard")).toBe("/dashboard");
    expect(resolvePostLoginDestination("/dashboard?tab=overview")).toBe(
      "/dashboard?tab=overview",
    );
  });

  it("preserves valid deep links such as /analysis?symbol=HDFCBANK", () => {
    expect(resolvePostLoginDestination("/analysis?symbol=HDFCBANK")).toBe(
      "/analysis?symbol=HDFCBANK",
    );
    expect(resolvePostLoginDestination("/analysis?symbol=TCS.NS&mode=simple")).toBe(
      "/analysis?symbol=TCS.NS&mode=simple",
    );
  });

  it("preserves internal application paths", () => {
    expect(resolvePostLoginDestination("/settings")).toBe("/settings");
    expect(resolvePostLoginDestination("/compare?symbols=TCS,INFY")).toBe(
      "/compare?symbols=TCS,INFY",
    );
    expect(resolvePostLoginDestination("/research")).toBe("/research");
  });

  it("rejects open redirect / protocol-relative URLs and falls back to /dashboard", () => {
    expect(resolvePostLoginDestination("//evil.com")).toBe("/dashboard");
    expect(resolvePostLoginDestination("https://evil.com/phish")).toBe("/dashboard");
    expect(resolvePostLoginDestination("http://attacker.com")).toBe("/dashboard");
    expect(resolvePostLoginDestination("javascript:alert(1)")).toBe("/dashboard");
  });

  it("rejects relative path traversal and relative paths without leading slash", () => {
    expect(resolvePostLoginDestination("relative/path")).toBe("/dashboard");
    expect(resolvePostLoginDestination("../evil")).toBe("/dashboard");
  });
});

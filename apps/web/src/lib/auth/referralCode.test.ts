/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it } from "vitest";

import {
  REFERRAL_CODE_STORAGE_KEY,
  clearReferralCode,
  readReferralCode,
  rememberReferralCode,
} from "./referralCode";

afterEach(() => {
  window.history.replaceState({}, "", "/");
  sessionStorage.clear();
});

describe("referral code hand-off", () => {
  it("stores a signup ref and reads it on the register page", () => {
    window.history.replaceState({}, "", "/signup?ref=dspabc12345");
    expect(readReferralCode()).toBe("DSPABC12345");
    window.history.replaceState({}, "", "/register");
    expect(readReferralCode()).toBe("DSPABC12345");
    expect(sessionStorage.getItem(REFERRAL_CODE_STORAGE_KEY)).toBe("DSPABC12345");
  });

  it("rejects codes that are not a referral token", () => {
    expect(rememberReferralCode("")).toBeNull();
    expect(rememberReferralCode("bad code")).toBeNull();
    expect(rememberReferralCode("ok")).toBeNull();
  });

  it("clears the stored code after registration", () => {
    rememberReferralCode("DSPABC12345");
    clearReferralCode();
    window.history.replaceState({}, "", "/register");
    expect(readReferralCode()).toBeNull();
  });
});

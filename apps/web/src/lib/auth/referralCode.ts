/** Session hand-off for `?ref=` so account creation can send the code to the server. */

export const REFERRAL_CODE_STORAGE_KEY = "dsp.referral.code";

const CODE_PATTERN = /^[A-Z0-9-]{4,64}$/;

export function normalizeReferralCode(raw: string | null | undefined): string | null {
  const code = String(raw || "").trim().toUpperCase();
  if (!CODE_PATTERN.test(code)) return null;
  return code;
}

export function rememberReferralCode(raw: string | null | undefined): string | null {
  const code = normalizeReferralCode(raw);
  if (!code || typeof sessionStorage === "undefined") return code;
  sessionStorage.setItem(REFERRAL_CODE_STORAGE_KEY, code);
  return code;
}

/** Prefer the URL `ref` query, then the value stored while visiting /signup. */
export function readReferralCode(): string | null {
  if (typeof window === "undefined") return null;
  const fromUrl = new URLSearchParams(window.location.search).get("ref");
  if (fromUrl) return rememberReferralCode(fromUrl);
  try {
    return normalizeReferralCode(sessionStorage.getItem(REFERRAL_CODE_STORAGE_KEY));
  } catch {
    return null;
  }
}

export function clearReferralCode(): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.removeItem(REFERRAL_CODE_STORAGE_KEY);
}

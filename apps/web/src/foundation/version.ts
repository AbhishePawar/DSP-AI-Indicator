/** EPS-003 — Version 2.0 Release Candidate hardening. */

export const FRONTEND_FOUNDATION_VERSION = "2.0.0-rc.1" as const;

export const FRONTEND_FOUNDATION_EPIC = "EPS-003" as const;

export const FRONTEND_FOUNDATION_STATUS = "release-candidate" as const;

/** Target backend package for this frontend channel. */
export const BACKEND_PLATFORM_TARGET = "dsp_platform@2.0.0" as const;

/** Frozen analyse contract label — no behaviour changes. */
export const API_CONTRACT_TARGET = "v1.0.0" as const;

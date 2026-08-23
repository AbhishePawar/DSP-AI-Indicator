/** Strongly typed authentication models — frontend session only. */

export type AuthenticationStatus =
  | "restoring"
  | "loading"
  | "authenticated"
  | "unauthenticated"
  | "expired"
  | "refreshing";

export type User = {
  subject: string;
  username: string;
  displayName: string;
  email: string | null;
  role: string;
  roles: string[];
  permissions: string[];
};

export type Session = {
  accessToken: string;
  refreshToken: string | null;
  tokenType: string;
  role: string;
  roles: string[];
  permissions: string[];
  subject: string;
  username: string;
  displayName: string;
  email: string | null;
  authMethod: string;
  sessionId: string | null;
  issuedAt: string;
  expiresAt: string | null;
  rememberMe: boolean;
};

export type AuthState = {
  status: AuthenticationStatus;
  session: Session | null;
  user: User | null;
};

export type LoginCredentials = {
  username: string;
  password?: string;
  rememberMe?: boolean;
  /** Prefer A009 RBAC when true (default). */
  useRbac?: boolean;
  /** Use enterprise multi-provider password login (email or username). */
  useEnterprise?: boolean;
};

/** @deprecated Use Session — kept for gradual migration. */
export type AuthSession = Session;

/**
 * Additive, non-breaking MFA step-up signal from the EnterpriseAuthPlatform.
 *
 * The backend always issues a full session on primary login (password / OTP /
 * OAuth / magic-link); when `DSP_AUTH_MFA=true` and a user has an enrolled
 * factor, the login response additionally carries these fields so the
 * frontend can present a step-up challenge without blocking the session or
 * requiring a page refresh. See `packages/auth/src/auth/mfa.py` (MfaGateway).
 */
export type MfaChallengeInfo = {
  mfaToken: string | null;
  methods: string[];
};

export function userFromSession(session: Session): User {
  return {
    subject: session.subject,
    username: session.username,
    displayName: session.displayName,
    email: session.email,
    role: session.role,
    roles: session.roles,
    permissions: session.permissions,
  };
}

export function sessionStatusLabel(status: AuthenticationStatus): string {
  switch (status) {
    case "restoring":
      return "Restoring session";
    case "loading":
      return "Loading";
    case "authenticated":
      return "Authenticated";
    case "unauthenticated":
      return "Not signed in";
    case "expired":
      return "Session expired";
    case "refreshing":
      return "Refreshing session";
    default:
      return "Unknown";
  }
}

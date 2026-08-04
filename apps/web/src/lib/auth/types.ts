/** Strongly typed authentication models — frontend session only. */

export type AuthenticationStatus =
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
};

/** @deprecated Use Session — kept for gradual migration. */
export type AuthSession = Session;

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

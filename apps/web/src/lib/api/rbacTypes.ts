/** A009 institutional auth API types — transport only. */

export type RbacUser = {
  user_id: string;
  username: string;
  email: string;
  display_name: string;
  status: string;
  created_at: string;
  updated_at: string;
  last_login: string | null;
  roles: string[];
  metadata?: Record<string, unknown>;
};

export type RbacTokens = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  session_id: string | null;
};

export type RbacSession = {
  session_id: string;
  user_id: string;
  created_at: string;
  expires_at: string;
  revoked: boolean;
  refresh_token_id: string | null;
  metadata?: Record<string, unknown>;
};

export type RbacLoginResult = {
  user: RbacUser;
  tokens: RbacTokens;
  session: RbacSession;
};

export type RbacEnvelope<T> = {
  ok: boolean;
  result?: T;
  error?: string;
  message?: string | null;
  schema?: unknown;
};

/**
 * EPIC-F008 / A010 administration API types — transport only.
 * No client-side administration logic.
 */

export type AdminEnvelope<T> = {
  ok: boolean;
  result?: T;
  schema?: unknown;
  error?: string;
  message?: string | null;
};

export type AdminSchema = {
  schema_version?: string;
  service_version?: string;
  capabilities?: string[];
  rules?: string[];
};

export type AdminDashboard = {
  generated_at?: string;
  users_count?: number;
  sessions_count?: number;
  active_sessions_count?: number;
  audit_records_count?: number;
  workflow_records_count?: number;
  research_refs_count?: number;
  roles_count?: number;
  permissions_count?: number;
  health_status?: string;
  metadata?: Record<string, unknown>;
};

export type AdminUser = {
  user_id: string;
  username: string;
  email: string;
  display_name?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  last_login?: string | null;
  roles?: string[];
  metadata?: Record<string, unknown>;
};

export type AdminRole = {
  role_id: string;
  name?: string;
  permissions?: string[];
  configurable?: boolean;
};

export type AdminSession = {
  session_id: string;
  user_id: string;
  created_at?: string;
  expires_at?: string;
  revoked?: boolean;
  refresh_token_id?: string | null;
  metadata?: Record<string, unknown>;
};

export type AdminEntity = {
  entity_id?: string;
  kind?: string;
  created_at?: string;
  updated_at?: string;
  version?: string | number;
  payload?: Record<string, unknown>;
  refs?: Record<string, unknown>;
  provenance?: Record<string, unknown>;
};

export type AdminTimelineItem = {
  kind?: string;
  entity_id?: string;
  created_at?: string;
  summary?: Record<string, unknown>;
};

export type AdminSearchResult = {
  scope?: string;
  query?: string;
  count?: number;
  results?: unknown[];
};

export type AdminAuditExport = {
  export_kind?: string;
  count?: number;
  records?: unknown[];
  rules?: string[];
};

export type AdminHealthCheck = {
  name?: string;
  status?: string;
  message?: string;
};

export type AdminHealthPanel = {
  status?: string;
  ready?: boolean;
  checks?: AdminHealthCheck[];
  rules?: string[];
};

export type AdminConfigItem = {
  key?: string;
  set?: boolean;
  value?: string | null;
  secret?: boolean;
};

export type AdminConfiguration = {
  source?: string;
  count?: number;
  items?: AdminConfigItem[];
  message?: string | null;
};

export type AdminPackageVersion = {
  package?: string;
  version?: string;
};

export type AdminVersions = {
  packages?: AdminPackageVersion[];
};

export type AdminFeatureFlags = {
  source?: string;
  flags?: Record<string, boolean>;
  message?: string | null;
};

export type AdminMetrics = {
  users?: number;
  sessions_total?: number;
  sessions_active?: number;
  audit_records?: number;
  workflow_records?: number;
  approval_history?: number;
  research_refs?: number;
  citations?: number;
  provenance?: number;
  metadata_entities?: number;
};

export type AdminAuditFilters = {
  query?: string;
  subject?: string;
  workflow_id?: string;
  event_type?: string;
};

export type AdminSearchScope = "audit" | "workflow" | "users" | "sessions";

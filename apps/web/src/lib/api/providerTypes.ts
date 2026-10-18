/**
 * Types for Provider & API Management and Task Routing (Admin).
 */

export type ProviderHealthStatus =
  | "healthy"
  | "configured_untested"
  | "degraded"
  | "error"
  | "unreachable"
  | "rate_limited"
  | "quota_exhausted"
  | "timeout"
  | "provider_outage"
  | "config_error"
  | "network_error"
  | "auth_failure"
  | "expired_token"
  | "permission_failure"
  | "unsupported"
  | "not_configured";

export type ProviderCategory = "ai" | "market_data";

export type ProviderRecord = {
  provider_id: string;
  display_name: string;
  category: ProviderCategory;
  selected_model: string;
  available_models: string[];
  is_active: boolean;
  has_credential: boolean;
  masked_credential?: string | null;
  health_status: ProviderHealthStatus;
  supported_capabilities: string[];
  last_tested_at: string | null;
  last_latency_ms: number | null;
  last_test_success?: boolean | null;
  error_message: string | null;
  recommended_action?: string | null;
  version: number;
  requires_credential: boolean;
};

export type ProvidersListResponse = {
  providers: ProviderRecord[];
  total: number;
};

export type ConnectionTestRequest = {
  secret?: string;
  model?: string;
};

export type ConnectionTestResponse = {
  success: boolean;
  status: string;
  latency_ms: number;
  sanitized_error?: string | null;
  recommended_action?: string | null;
  timestamp?: string;
};

export type SaveCredentialRequest = {
  secret: string;
  validate?: boolean;
  selected_model?: string;
};

export type SaveCredentialResponse = {
  ok: boolean;
  provider_id: string;
  health_status: ProviderHealthStatus;
  provider: ProviderRecord;
};

export type UpdateStatusRequest = {
  is_active: boolean;
};

export type UpdateModelRequest = {
  model: string;
};

export type ProviderAuditLog = {
  timestamp: string;
  action: string;
  provider_id: string;
  author: string;
  version: number;
  details?: Record<string, unknown>;
};

export type ProviderAuditResponse = {
  provider_id: string;
  audit_log: ProviderAuditLog[];
};

export type TaskRoutingPolicy = {
  task_id: string;
  primary_provider: string;
  fallback_providers: string[];
  require_independent_corroboration: boolean;
  timeout_seconds: number;
  max_retries: number;
};

export type TaskRoutingResponse = {
  policies: TaskRoutingPolicy[];
};

export type UpdateRoutingRequest = {
  primary_provider: string;
  fallback_providers?: string[];
  require_independent_corroboration?: boolean;
  timeout_seconds?: number;
  max_retries?: number;
};

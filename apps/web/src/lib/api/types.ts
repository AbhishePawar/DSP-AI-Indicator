/** API transport types — mirror backend schemas; no business semantics. */

import type { CompositionErrorBody } from "@/lib/api/compositionTypes";

export type ApiErrorBody = {
  ok: false;
  error: string;
  detail: string | null;
  message?: string | null;
  error_code?: string | null;
  pipeline_stage?: string | null;
  validation_errors?: string[];
  correlation_id?: string | null;
  timestamp?: string | null;
  api_version: string;
  status_code: number;
} & Partial<CompositionErrorBody>;

export type ApiResponse<T = unknown> = {
  ok: boolean;
  capability: string;
  payload: T;
  limitations: string[];
  errors: string[];
  api_version: string;
  platform_version: string | null;
};

export type HealthResponse = {
  status: string;
  ready: boolean;
  api_version: string;
  platform_version: string | null;
  pipeline_version?: string | null;
  repository_version?: string | null;
  checks: Array<{ name: string; status: string; message: string }>;
  limitations: string[];
};

export type PlatformInfoResponse = {
  name: string;
  version: string;
  status: string;
  environment: string;
  capabilities: string[];
  registered_services: string[];
  generated_at: string;
  notes: string[];
  api_version: string;
};

export type LoginPayload = {
  access_token: string;
  token_type: string;
  role: string;
  subject: string;
  username?: string;
  auth_method: string;
};

export type AnalyzeCompanyPayload = {
  report_id: string;
  result: unknown;
};

export type ReportResponse = {
  report_id: string;
  format: string;
  report: unknown;
  api_version: string;
  limitations: string[];
};

export class ApiClientError extends Error {
  readonly status: number;
  readonly body: ApiErrorBody | null;

  constructor(message: string, status: number, body: ApiErrorBody | null = null) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.body = body;
  }
}

export type {
  AnalyseRequest,
  AnalyseResponse,
  CapabilitiesResponse,
  ValidateResponse,
  VersionResponse,
} from "@/lib/api/compositionTypes";


/** EPS-002 — Enterprise portal types (display-only thin client). */

export type EnterpriseEnvelope<T> = {
  ok: boolean;
  result?: T;
  schema?: unknown;
  message?: string | null;
  error?: string;
};

export type Organization = {
  org_id: string;
  name: string;
  slug: string;
  status: string;
  owner_user_id: string;
  seat_limit: number | null;
  branding: Record<string, unknown>;
  preferences: Record<string, unknown>;
};

export type LicenseInfo = {
  available: boolean;
  message: string | null;
  license: {
    license_id: string;
    tier: string;
    status: string;
    seats: number;
    expires_at: string | null;
    valid?: boolean;
  } | null;
};

export type BillingStatus = {
  available: boolean;
  message: string;
  provider: string;
  status: string;
  subscription: unknown;
  invoices: unknown[];
};

export type ApiKeyList = {
  keys: Array<{
    key_id: string;
    name: string;
    scopes: string[];
    status: string;
    created_at: string;
    expires_at: string | null;
  }>;
  message: string | null;
};

export type UsageSnapshot = {
  available: boolean;
  message: string | null;
  dau: number | null;
  research_count: number | null;
  export_count: number | null;
  comparison_count: number | null;
  api_request_count: number | null;
  storage_bytes: number | null;
};

export type CustomerPortal = {
  organization: Organization;
  license: LicenseInfo;
  members: Array<{
    user_id: string;
    role_id: string;
    status: string;
    permissions: string[];
  }>;
  members_message: string | null;
  usage: UsageSnapshot;
  billing: BillingStatus;
  api_keys: ApiKeyList;
  settings: {
    branding: Record<string, unknown>;
    preferences: Record<string, unknown>;
  };
};

export type OpsDashboard = {
  enterprise_health: {
    overall: string;
    components: Record<string, { status: string; detail: string }>;
  };
  organizations: number;
  active_sessions: number;
  usage: Record<string, unknown>;
  billing_provider: string;
  billing_available: boolean;
  deployments: { available: boolean; message: string };
  alerts: unknown[];
  services: Array<{ name: string; status: string }>;
  collaboration: {
    status: string;
    realtime: boolean;
    capabilities_reserved: string[];
  };
};

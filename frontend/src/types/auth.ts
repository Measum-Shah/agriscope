export type UserRole = 'farmer' | 'agronomist' | 'researcher' | 'admin';
export type UserPlan = 'free' | 'pro' | 'admin';
export type UserStatus = 'active' | 'suspended' | 'pending_verification' | 'deleted';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  plan: UserPlan;
  status: UserStatus;
  email_verified: boolean;
  totp_enabled: boolean;
  registration_date?: string;
  last_login?: string | null;
}

export interface Entitlements {
  plan: UserPlan;
  daily_prediction_limit: number | null;
  predictions_used_today: number;
  predictions_remaining_today: number | null;
  features: {
    manual_et: boolean;
    location_weather: boolean;
    single_field: boolean;
    basic_crops: boolean;
    export_csv: boolean;
    satellite_indices: boolean;
    sentinel_pipeline: boolean;
    custom_kc: boolean;
    advanced_crops: boolean;
    export_geojson: boolean;
    pdf_report: boolean;
    api_access: boolean;
    unlimited_fields: boolean;
    priority_inference: boolean;
  };
}

export interface SessionInfo {
  id: string;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
  expires_at: string;
  is_current?: boolean;
}

export interface AuditLogItem {
  id: string;
  actor?: string;
  action: string;
  target?: string;
  metadata_json?: Record<string, unknown>;
  timestamp: string;
  ip_address?: string;
  user_agent?: string;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
}

export interface LoginResponse {
  access_token?: string;
  token_type?: string;
  user?: User;
}

export interface TOTPSetupResponse {
  secret: string;
  provisioning_uri: string;
  qr_code_base64: string;
}

export interface TOTPVerifyResponse {
  enabled: boolean;
  recovery_codes: string[];
}

export interface ApiError {
  detail: string;
  code?: string;
  request_id?: string;
}

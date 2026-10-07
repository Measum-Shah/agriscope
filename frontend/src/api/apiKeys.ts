import { apiClient } from './client';

export interface ApiKeyItem {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  rate_limit_per_min: number;
  daily_limit: number;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  is_active: boolean;
}

export interface ApiKeyCreatedResponse {
  id: string;
  name: string;
  raw_key: string;
  key_prefix: string;
  scopes: string[];
  rate_limit_per_min: number;
  daily_limit: number;
  created_at: string;
  expires_at: string | null;
  warning: string;
}

export interface ApiKeyCreatePayload {
  name: string;
  scopes?: string[];
  rate_limit_per_min?: number;
  daily_limit?: number;
  expires_in_days?: number;
}

export interface ApiKeyUsageStats {
  api_key_id: string;
  requests_today: number;
  daily_limit: number;
  remaining_today: number;
  rate_limit_per_min: number;
  last_used_at: string | null;
  endpoints: Record<string, number>;
  status_codes: Record<string, number>;
}

export const apiKeysApi = {
  list: async (): Promise<ApiKeyItem[]> => {
    const res = await apiClient.get<ApiKeyItem[]>('/api-keys');
    return res.data;
  },

  create: async (payload: ApiKeyCreatePayload): Promise<ApiKeyCreatedResponse> => {
    const res = await apiClient.post<ApiKeyCreatedResponse>('/api-keys', payload);
    return res.data;
  },

  revoke: async (id: string): Promise<{ success: boolean; message: string }> => {
    const res = await apiClient.post<{ success: boolean; message: string }>(`/api-keys/${id}/revoke`);
    return res.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/api-keys/${id}`);
  },

  getUsage: async (id: string): Promise<ApiKeyUsageStats> => {
    const res = await apiClient.get<ApiKeyUsageStats>(`/api-keys/${id}/usage`);
    return res.data;
  },
};

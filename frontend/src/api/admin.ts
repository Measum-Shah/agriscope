import { apiClient } from './client';

export interface AdminUserItem {
  id: string;
  name: string;
  email: string;
  role: string;
  plan: string;
  status: string;
  email_verified: boolean;
  totp_enabled: boolean;
  failed_attempts: number;
  locked_until: string | null;
  registration_date: string;
  last_login: string | null;
}

export interface AdminUserAuditItem {
  id: string;
  actor: string;
  action: string;
  target: string | null;
  metadata_json: Record<string, unknown>;
  ip_address: string | null;
  user_agent: string | null;
  timestamp: string;
}

export interface PaginatedAdminUsers {
  items: AdminUserItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface DatasetItem {
  id: string;
  name: string;
  version: string;
  file_uri: string;
  file_hash: string;
  status: string;
  data_provenance: string;
  stats_json: Record<string, unknown>;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetUploadReport {
  id: string;
  name: string;
  version: string;
  status: string;
  row_count: number;
  columns: string[];
  stats: Record<string, unknown>;
  outlier_report: Record<string, unknown>;
  preview_rows: Record<string, unknown>[];
  validation_errors: string[];
  message: string;
}

export interface SystemMetrics {
  total_users: number;
  active_users: number;
  suspended_users: number;
  predictions_today: number;
  total_predictions: number;
  queue_depth: number;
  active_model: string | null;
  error_rate_pct: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
  storage_usage_bytes: number;
  uptime_seconds: number;
}

export interface FeatureFlagItem {
  id: string;
  name: string;
  description: string | null;
  is_enabled: boolean;
  rules_json: Record<string, unknown>;
}

export interface AnnouncementItem {
  id: string;
  title: string;
  message: string;
  type: string;
  is_active: boolean;
  starts_at: string | null;
  ends_at: string | null;
}

export interface SystemLimitsConfig {
  free_daily_prediction_limit: number;
  pro_daily_prediction_limit: number;
  free_max_fields: number;
  pro_max_fields: number;
  batch_max_rows: number;
  rate_limit_per_min_default: number;
  maintenance_mode: boolean;
}

export const adminApi = {
  // Users
  listUsers: async (params?: {
    search?: string;
    role?: string;
    plan?: string;
    status?: string;
    page?: number;
    size?: number;
  }): Promise<PaginatedAdminUsers> => {
    const res = await apiClient.get<PaginatedAdminUsers>('/admin/users', { params });
    return res.data;
  },

  updateRolePlan: async (userId: string, payload: { role?: string; plan?: string }): Promise<AdminUserItem> => {
    const res = await apiClient.patch<AdminUserItem>(`/admin/users/${userId}/role-plan`, payload);
    return res.data;
  },

  updateStatus: async (userId: string, status: string): Promise<AdminUserItem> => {
    const res = await apiClient.patch<AdminUserItem>(`/admin/users/${userId}/status`, { status });
    return res.data;
  },

  unlockUser: async (userId: string): Promise<AdminUserItem> => {
    const res = await apiClient.post<AdminUserItem>(`/admin/users/${userId}/unlock`);
    return res.data;
  },

  forceLogout: async (userId: string): Promise<{ success: boolean; revoked_sessions: number }> => {
    const res = await apiClient.post<{ success: boolean; revoked_sessions: number }>(`/admin/users/${userId}/force-logout`);
    return res.data;
  },

  deleteUser: async (userId: string): Promise<void> => {
    await apiClient.delete(`/admin/users/${userId}`);
  },

  getUserAudit: async (userId: string): Promise<AdminUserAuditItem[]> => {
    const res = await apiClient.get<AdminUserAuditItem[]>(`/admin/users/${userId}/audit`);
    return res.data;
  },

  // Datasets
  listDatasets: async (): Promise<DatasetItem[]> => {
    const res = await apiClient.get<DatasetItem[]>('/admin/datasets');
    return res.data;
  },

  uploadDataset: async (formData: FormData): Promise<DatasetUploadReport> => {
    const res = await apiClient.post<DatasetUploadReport>('/admin/datasets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  deleteDataset: async (datasetId: string): Promise<void> => {
    await apiClient.delete(`/admin/datasets/${datasetId}`);
  },

  // Metrics
  getMetrics: async (): Promise<SystemMetrics> => {
    const res = await apiClient.get<SystemMetrics>('/admin/metrics');
    return res.data;
  },

  // Audit Logs
  listAuditLogs: async (params?: {
    actor?: string;
    action?: string;
    target?: string;
    page?: number;
    size?: number;
  }): Promise<{ items: AdminUserAuditItem[]; total: number; page: number; size: number; pages: number }> => {
    const res = await apiClient.get('/admin/audit', { params });
    return res.data;
  },

  // System Settings
  listFeatureFlags: async (): Promise<FeatureFlagItem[]> => {
    const res = await apiClient.get<FeatureFlagItem[]>('/admin/system/feature-flags');
    return res.data;
  },

  updateFeatureFlag: async (payload: { name: string; is_enabled: boolean; description?: string }): Promise<FeatureFlagItem> => {
    const res = await apiClient.post<FeatureFlagItem>('/admin/system/feature-flags', payload);
    return res.data;
  },

  listAnnouncements: async (): Promise<AnnouncementItem[]> => {
    const res = await apiClient.get<AnnouncementItem[]>('/admin/system/announcements');
    return res.data;
  },

  createAnnouncement: async (payload: { title: string; message: string; type?: string; is_active?: boolean }): Promise<AnnouncementItem> => {
    const res = await apiClient.post<AnnouncementItem>('/admin/system/announcements', payload);
    return res.data;
  },

  toggleAnnouncement: async (id: string, is_active: boolean): Promise<AnnouncementItem> => {
    const res = await apiClient.patch<AnnouncementItem>(`/admin/system/announcements/${id}/status`, null, {
      params: { is_active },
    });
    return res.data;
  },

  getSystemLimits: async (): Promise<SystemLimitsConfig> => {
    const res = await apiClient.get<SystemLimitsConfig>('/admin/system/limits');
    return res.data;
  },

  updateSystemLimits: async (payload: SystemLimitsConfig): Promise<SystemLimitsConfig> => {
    const res = await apiClient.put<SystemLimitsConfig>('/admin/system/limits', payload);
    return res.data;
  },
};

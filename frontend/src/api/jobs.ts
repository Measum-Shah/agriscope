import { apiClient } from './client';

export interface BatchJobItem {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_rows: number;
  processed_rows: number;
  error_summary: {
    total_processed?: number;
    failed_count?: number;
    errors_sample?: Array<{ row: number; error: string }>;
    fatal_error?: string;
  };
  output_file_uri?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportItem {
  id: string;
  title: string;
  format: 'pdf' | 'csv' | 'xlsx' | 'png';
  file_size_bytes: number;
  status: string;
  download_url?: string | null;
  created_at: string;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'warning' | 'alert' | 'system';
  is_read: boolean;
  metadata_json: Record<string, any>;
  created_at: string;
}

export interface NotificationPreferences {
  email_enabled: boolean;
  sms_enabled: boolean;
  in_app_enabled: boolean;
  irrigation_alerts: boolean;
  system_announcements: boolean;
}

export const jobsApi = {
  // Batch APIs
  getTemplate: async (): Promise<{ filename: string; csv_content: string }> => {
    const response = await apiClient.get<{ filename: string; csv_content: string }>('/batch/template');
    return response.data;
  },

  uploadBatchCsv: async (file: File): Promise<{ job_id: string; status: string; total_rows: number; message: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post('/batch/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  getBatchStatus: async (jobId: string): Promise<BatchJobItem> => {
    const response = await apiClient.get<BatchJobItem>(`/batch/status/${jobId}`);
    return response.data;
  },

  getBatchDownloadUrl: async (jobId: string): Promise<{ download_url: string; filename: string }> => {
    const response = await apiClient.get<{ download_url: string; filename: string }>(`/batch/download/${jobId}`);
    return response.data;
  },

  // Reports APIs
  generateReport: async (payload: { title: string; format: string; parameters?: Record<string, any> }): Promise<ReportItem> => {
    const response = await apiClient.post<ReportItem>('/reports/generate', payload);
    return response.data;
  },

  listReports: async (): Promise<ReportItem[]> => {
    const response = await apiClient.get<ReportItem[]>('/reports/list');
    return response.data;
  },

  // Notifications APIs
  listNotifications: async (unreadOnly = false): Promise<NotificationItem[]> => {
    const response = await apiClient.get<NotificationItem[]>('/notifications', {
      params: { unread_only: unreadOnly },
    });
    return response.data;
  },

  markRead: async (id: string): Promise<NotificationItem> => {
    const response = await apiClient.patch<NotificationItem>(`/notifications/${id}/read`);
    return response.data;
  },

  markAllRead: async (): Promise<{ ok: boolean; marked_count: number }> => {
    const response = await apiClient.post<{ ok: boolean; marked_count: number }>('/notifications/mark-all-read');
    return response.data;
  },

  getPreferences: async (): Promise<NotificationPreferences> => {
    const response = await apiClient.get<NotificationPreferences>('/notifications/preferences');
    return response.data;
  },

  updatePreferences: async (payload: Partial<NotificationPreferences>): Promise<NotificationPreferences> => {
    const response = await apiClient.put<NotificationPreferences>('/notifications/preferences', payload);
    return response.data;
  },
};

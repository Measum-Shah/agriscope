import { apiClient } from './client';
import { PredictResponse } from './predict';

export interface HistoryFilterParams {
  page?: number;
  per_page?: number;
  start_date?: string;
  end_date?: string;
  classification?: string;
  model_id?: string;
  field_id?: string;
  is_saved?: boolean;
  search?: string;
}

export interface HistoryListResponse {
  items: PredictResponse[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface HistoryUpdatePayload {
  is_saved?: boolean;
  tags?: string[];
  note?: string;
}

export interface HistoryStatsResponse {
  total_predictions: number;
  today_predictions: number;
  quota_remaining_today: number | null;
  quota_limit_today: number | null;
  mean_et: number;
  latest_et: number | null;
  classification_counts: Record<string, number>;
  trend_7d: Array<{ date: string; mean_et: number; count: number }>;
}

export const historyApi = {
  list: async (params: HistoryFilterParams = {}): Promise<HistoryListResponse> => {
    const res = await apiClient.get<HistoryListResponse>('/history', { params });
    return res.data;
  },

  getStats: async (): Promise<HistoryStatsResponse> => {
    const res = await apiClient.get<HistoryStatsResponse>('/history/stats');
    return res.data;
  },

  update: async (id: string, payload: HistoryUpdatePayload): Promise<PredictResponse> => {
    const res = await apiClient.patch<PredictResponse>(`/history/${id}`, payload);
    return res.data;
  },

  delete: async (id: string): Promise<{ deleted: boolean }> => {
    const res = await apiClient.delete<{ deleted: boolean }>(`/history/${id}`);
    return res.data;
  },

  bulkDelete: async (prediction_ids: string[]): Promise<{ deleted_count: number }> => {
    const res = await apiClient.post<{ deleted_count: number }>('/history/bulk-delete', {
      prediction_ids,
    });
    return res.data;
  },
};

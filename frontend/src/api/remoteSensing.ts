import { apiClient } from './client';

export interface RemoteSensingObservationItem {
  id: string;
  field_id: string;
  observation_date: string;
  ndvi?: number | null;
  evi?: number | null;
  ndwi?: number | null;
  cloud_cover_pct?: number | null;
  et0?: number | null;
  kc?: number | null;
  etc?: number | null;
  rain_mm?: number | null;
}

export interface RemoteSensingAnalysisResponse {
  field_id: string;
  field_name: string;
  crop_name?: string | null;
  observations_count: number;
  provider: string;
  date_range: {
    start_date: string;
    end_date: string;
  };
  observations: RemoteSensingObservationItem[];
}

export interface AnalyzeFieldParams {
  start_date?: string;
  end_date?: string;
  max_cloud_cover?: number;
  provider?: 'sentinel' | 'gee' | 'mock';
}

export const remoteSensingApi = {
  analyzeField: async (
    fieldId: string,
    params?: AnalyzeFieldParams
  ): Promise<RemoteSensingAnalysisResponse> => {
    const response = await apiClient.post<RemoteSensingAnalysisResponse>(
      `/remote-sensing/analyze/${fieldId}`,
      null,
      { params }
    );
    return response.data;
  },

  getObservations: async (
    fieldId: string,
    params?: { start_date?: string; end_date?: string }
  ): Promise<RemoteSensingObservationItem[]> => {
    const response = await apiClient.get<RemoteSensingObservationItem[]>(
      `/remote-sensing/observations/${fieldId}`,
      { params }
    );
    return response.data;
  },
};

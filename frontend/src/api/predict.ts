import { apiClient } from './client';

export interface PredictRequest {
  temperature: number;
  humidity: number;
  wind_speed: number;
  solar_radiation: number;
  tmin?: number;
  tmax?: number;
  latitude?: number;
  elevation?: number;
  doy?: number;
  field_id?: string;
  source?: 'manual' | 'location' | 'batch' | 'api';
  tags?: string[];
  note?: string;
  is_saved?: boolean;
}

export interface PredictResponse {
  id?: string;
  et_value: number;
  interval_low: number;
  interval_high: number;
  confidence_level: number;
  classification: 'low' | 'moderate' | 'high';
  fao56_reference_et0?: number;
  irrigation_interpretation: string;
  model_id: string;
  model_name: string;
  model_version: string;
  model_algorithm: string;
  data_provenance: string;
  metrics?: Record<string, number>;
  source: string;
  is_saved: boolean;
  tags: string[];
  note?: string;
  created_at: string;
}

export interface ComparePredictResponse {
  ensemble: PredictResponse;
  models: Array<{
    model_id: string;
    model_name: string;
    algorithm: string;
    version: string;
    et_value: number;
    interval_low: number;
    interval_high: number;
    classification: string;
    metrics?: Record<string, number>;
  }>;
}

export interface ShapContribution {
  feature: string;
  contribution: number;
  base_value: number;
}

export interface ExplainPredictResponse {
  prediction_id?: string;
  et_value: number;
  base_value: number;
  contributions: ShapContribution[];
  algorithm: string;
  model_version: string;
}

export interface MeteorologicalSample {
  temperature: number;
  humidity: number;
  wind_speed: number;
  solar_radiation: number;
  tmin: number;
  tmax: number;
  latitude: number;
  elevation: number;
  doy: number;
  location_name: string;
  description: string;
}

export const predictApi = {
  predict: async (data: PredictRequest, persist: boolean = true): Promise<PredictResponse> => {
    const res = await apiClient.post<PredictResponse>(`/predict?persist=${persist}`, data);
    return res.data;
  },

  compare: async (data: PredictRequest): Promise<ComparePredictResponse> => {
    const res = await apiClient.post<ComparePredictResponse>('/predict/compare', data);
    return res.data;
  },

  explain: async (data: PredictRequest): Promise<ExplainPredictResponse> => {
    const res = await apiClient.post<ExplainPredictResponse>('/predict/explain', data);
    return res.data;
  },

  getSample: async (): Promise<MeteorologicalSample> => {
    const res = await apiClient.get<MeteorologicalSample>('/predict/sample');
    return res.data;
  },
};

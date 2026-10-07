import { apiClient } from './client';

export interface CropStageItem {
  id: string;
  crop_id: string;
  stage_name: string;
  duration_days: number;
}

export interface CropDetail {
  id: string;
  name: string;
  scientific_name?: string | null;
  kc_ini: number;
  kc_mid: number;
  kc_end: number;
  description?: string | null;
  stages: CropStageItem[];
}

export interface IrrigationEventItem {
  id: string;
  field_id: string;
  event_date: string;
  water_applied_mm: number;
  method: string;
  notes?: string | null;
}

export interface LogIrrigationPayload {
  event_date: string;
  water_applied_mm: number;
  method: string;
  notes?: string;
}

export interface SoilBalanceDayItem {
  date: string;
  et0_mm: number;
  kc: number;
  etc_mm: number;
  rain_mm: number;
  effective_rain_mm: number;
  irrigation_applied_mm: number;
  root_depth_m: number;
  taw_mm: number;
  raw_mm: number;
  depletion_mm: number;
  is_stress: boolean;
  irrigation_recommended_mm: number;
}

export interface IrrigationScheduleDayItem {
  date: string;
  day_name: string;
  depletion_mm: number;
  raw_threshold_mm: number;
  is_irrigation_due: boolean;
  recommended_depth_mm: number;
  recommended_volume_m3_per_ha: number;
  recommended_volume_m3_total: number;
  reason: string;
}

export interface SeasonSummaryData {
  total_etc_mm: number;
  total_rainfall_mm: number;
  total_effective_rain_mm: number;
  total_irrigation_applied_mm: number;
  net_irrigation_requirement_mm: number;
  current_depletion_mm: number;
  raw_mm: number;
  taw_mm: number;
  status: 'optimal' | 'caution' | 'stress' | 'saturated';
}

export interface FieldIrrigationPlanData {
  field_id: string;
  field_name: string;
  crop_name?: string | null;
  area_ha: number;
  soil_type: string;
  planting_date?: string | null;
  mad_fraction: number;
  summary: SeasonSummaryData;
  schedule: IrrigationScheduleDayItem[];
  daily_balance: SoilBalanceDayItem[];
  events: IrrigationEventItem[];
}

export interface GetPlanParams {
  soil_type?: string;
  mad_fraction?: number;
  forecast_days?: number;
}

export const irrigationApi = {
  getPlan: async (fieldId: string, params?: GetPlanParams): Promise<FieldIrrigationPlanData> => {
    const response = await apiClient.get<FieldIrrigationPlanData>(`/irrigation/plan/${fieldId}`, {
      params,
    });
    return response.data;
  },

  getEvents: async (fieldId: string): Promise<IrrigationEventItem[]> => {
    const response = await apiClient.get<IrrigationEventItem[]>(`/irrigation/events/${fieldId}`);
    return response.data;
  },

  logEvent: async (fieldId: string, payload: LogIrrigationPayload): Promise<IrrigationEventItem> => {
    const response = await apiClient.post<IrrigationEventItem>(
      `/irrigation/events/${fieldId}`,
      payload
    );
    return response.data;
  },

  deleteEvent: async (fieldId: string, eventId: string): Promise<{ ok: boolean; message: string }> => {
    const response = await apiClient.delete<{ ok: boolean; message: string }>(
      `/irrigation/events/${fieldId}/${eventId}`
    );
    return response.data;
  },

  getCrops: async (): Promise<CropDetail[]> => {
    const response = await apiClient.get<CropDetail[]>('/crops');
    return response.data;
  },

  getCropDetail: async (cropId: string): Promise<CropDetail> => {
    const response = await apiClient.get<CropDetail>(`/crops/${cropId}`);
    return response.data;
  },
};

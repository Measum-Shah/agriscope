import { apiClient } from './client';

export interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][]; // [ [ [lon, lat], [lon, lat], ... ] ]
}

export interface FieldItem {
  id: string;
  name: string;
  crop_id?: string | null;
  crop_name?: string | null;
  planting_date?: string | null;
  area_ha: number;
  geometry: GeoJSONPolygon;
  created_at: string;
  updated_at: string;
}

export interface CreateFieldPayload {
  name: string;
  crop_id?: string | null;
  planting_date?: string | null;
  geometry: GeoJSONPolygon;
}

export interface UpdateFieldPayload {
  name?: string;
  crop_id?: string | null;
  planting_date?: string | null;
  geometry?: GeoJSONPolygon;
}

export interface CropOption {
  id: string;
  name: string;
  scientific_name?: string | null;
  kc_ini: number;
  kc_mid: number;
  kc_end: number;
}

export const fieldsApi = {
  getFields: async (): Promise<FieldItem[]> => {
    const response = await apiClient.get<FieldItem[]>('/fields');
    return response.data;
  },

  getField: async (id: string): Promise<FieldItem> => {
    const response = await apiClient.get<FieldItem>(`/fields/${id}`);
    return response.data;
  },

  createField: async (payload: CreateFieldPayload): Promise<FieldItem> => {
    const response = await apiClient.post<FieldItem>('/fields', payload);
    return response.data;
  },

  updateField: async (id: string, payload: UpdateFieldPayload): Promise<FieldItem> => {
    const response = await apiClient.put<FieldItem>(`/fields/${id}`, payload);
    return response.data;
  },

  deleteField: async (id: string): Promise<{ ok: boolean; message: string }> => {
    const response = await apiClient.delete<{ ok: boolean; message: string }>(`/fields/${id}`);
    return response.data;
  },

  getCrops: async (): Promise<CropOption[]> => {
    const response = await apiClient.get<CropOption[]>('/fields/crops');
    return response.data;
  },
};

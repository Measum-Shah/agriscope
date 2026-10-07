import { apiClient } from './client';

export interface WeatherPrefillResponse {
  date: string;
  temperature: number;
  humidity: number;
  wind_speed: number;
  solar_radiation: number;
  tmin?: number;
  tmax?: number;
  precipitation_mm?: number;
  et0_provider?: number;
  provider_name: string;
  is_fallback: boolean;
  is_cached: boolean;
}

export interface ForecastDayItem {
  date: string;
  temperature: number;
  humidity: number;
  wind_speed: number;
  solar_radiation: number;
  precipitation_mm: number;
  et0_ml: number;
  interval_low: number;
  interval_high: number;
  et0_provider?: number;
}

export interface ForecastResponse {
  latitude: number;
  longitude: number;
  days: number;
  provider: string;
  is_fallback: boolean;
  is_cached: boolean;
  forecast: ForecastDayItem[];
}

export interface MonthlyAggregationItem {
  month: string;
  mean_et0: number;
  total_days: number;
}

export interface HistoricalSeriesResponse {
  latitude: number;
  longitude: number;
  start_date: string;
  end_date: string;
  provider: string;
  is_fallback: boolean;
  is_cached: boolean;
  series: Array<{
    date: string;
    temperature: number;
    humidity: number;
    wind_speed: number;
    solar_radiation: number;
    precipitation_mm?: number;
    et0_provider?: number;
    provider_name: string;
    is_fallback: boolean;
  }>;
  monthly_summary: MonthlyAggregationItem[];
}

export interface GeocodingResultItem {
  name: string;
  country: string;
  latitude: number;
  longitude: number;
  admin1?: string;
  elevation?: number;
}

export const weatherApi = {
  getPrefill: async (
    latitude: number,
    longitude: number,
    targetDate?: string
  ): Promise<WeatherPrefillResponse> => {
    const res = await apiClient.get<WeatherPrefillResponse>('/weather/prefill', {
      params: { latitude, longitude, target_date: targetDate },
    });
    return res.data;
  },

  getForecast: async (
    latitude: number,
    longitude: number,
    days: number = 7
  ): Promise<ForecastResponse> => {
    const res = await apiClient.get<ForecastResponse>('/weather/forecast', {
      params: { latitude, longitude, days },
    });
    return res.data;
  },

  getHistorical: async (
    latitude: number,
    longitude: number,
    startDate: string,
    endDate: string
  ): Promise<HistoricalSeriesResponse> => {
    const res = await apiClient.get<HistoricalSeriesResponse>('/weather/historical', {
      params: {
        latitude,
        longitude,
        start_date: startDate,
        end_date: endDate,
      },
    });
    return res.data;
  },

  geocode: async (query: string): Promise<GeocodingResultItem[]> => {
    const res = await apiClient.get<GeocodingResultItem[]>('/weather/geocode', {
      params: { query },
    });
    return res.data;
  },
};

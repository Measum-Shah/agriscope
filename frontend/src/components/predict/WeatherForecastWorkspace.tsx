import React, { useState } from 'react';
import { CloudSun, History, Loader2, MapPin } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { PointPickerMap } from '../maps/PointPickerMap';
import { ForecastChart } from '../charts/ForecastChart';
import { HistoricalAggregationChart } from '../charts/HistoricalAggregationChart';
import {
  weatherApi,
  ForecastResponse,
  HistoricalSeriesResponse,
} from '../../api/weather';
import { useToast } from '../ui/Toast';

export const WeatherForecastWorkspace: React.FC = () => {
  const { toast } = useToast();
  const [lat, setLat] = useState(31.5204);
  const [lon, setLon] = useState(74.3587);
  const [place, setPlace] = useState('Lahore, Pakistan');

  const [isLoadingForecast, setIsLoadingForecast] = useState(false);
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);

  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [historicalData, setHistoricalData] = useState<HistoricalSeriesResponse | null>(null);

  const handleFetchForecast = async () => {
    setIsLoadingForecast(true);
    try {
      const res = await weatherApi.getForecast(lat, lon, 7);
      setForecastData(res);
      toast({
        title: '7-Day ET₀ Forecast Computed',
        description: `Source: ${res.provider.toUpperCase()}${res.is_fallback ? ' (Mock Fallback)' : ''}`,
        type: res.is_fallback ? 'warning' : 'success',
      });
    } catch {
      toast({ title: 'Forecast Failed', description: 'Could not fetch forecast.', type: 'error' });
    } finally {
      setIsLoadingForecast(false);
    }
  };

  const handleFetchHistorical = async () => {
    setIsLoadingHistory(true);
    try {
      // Last 180 days
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - 180);

      const res = await weatherApi.getHistorical(
        lat,
        lon,
        start.toISOString().substring(0, 10),
        end.toISOString().substring(0, 10)
      );
      setHistoricalData(res);
      toast({
        title: 'Historical Series Loaded',
        description: `Aggregated ${res.series.length} observations from ${res.provider.toUpperCase()}`,
        type: 'success',
      });
    } catch {
      toast({ title: 'Historical Query Failed', type: 'error' });
    } finally {
      setIsLoadingHistory(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CloudSun className="h-5 w-5 text-primary" />
              <div>
                <CardTitle className="text-base">Weather Forecast & Climatology Explorer</CardTitle>
                <CardDescription className="text-xs">
                  Pick a parcel location to generate ML-driven 7-day ET₀ forecasts and historical seasonal series.
                </CardDescription>
              </div>
            </div>
            {forecastData && (
              <Badge variant={forecastData.is_fallback ? 'warning' : 'secondary'} className="text-xs">
                {forecastData.provider} {forecastData.is_cached && '(Cached)'}
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <PointPickerMap
            latitude={lat}
            longitude={lon}
            onLocationSelect={(newLat, newLon, newPlace) => {
              setLat(newLat);
              setLon(newLon);
              if (newPlace) setPlace(newPlace);
            }}
            height={220}
          />

          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-border/50">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <MapPin className="h-3.5 w-3.5 text-primary" />
              <span>Location: <strong>{place}</strong></span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="default"
                size="sm"
                onClick={handleFetchForecast}
                disabled={isLoadingForecast}
                className="gap-1.5 text-xs h-8"
              >
                {isLoadingForecast ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <CloudSun className="h-3.5 w-3.5" />
                )}
                Compute 7-Day ET₀ Forecast
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleFetchHistorical}
                disabled={isLoadingHistory}
                className="gap-1.5 text-xs h-8"
              >
                {isLoadingHistory ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <History className="h-3.5 w-3.5" />
                )}
                Load Seasonal History
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 7-Day Forecast Chart Display */}
      {forecastData && (
        <Card className="p-4 space-y-2">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-semibold text-foreground">
              7-Day Crop Evapotranspiration Forecast (ET₀)
            </h3>
            <span className="text-[11px] text-muted-foreground">
              ML Model + Open-Meteo FAO-56 cross-check
            </span>
          </div>
          <ForecastChart data={forecastData.forecast} height={250} />
        </Card>
      )}

      {/* Historical Monthly Aggregation */}
      {historicalData && (
        <Card className="p-4 space-y-2">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-semibold text-foreground">
              Historical Monthly Evapotranspiration Pattern (6 Months)
            </h3>
            <span className="text-[11px] text-muted-foreground">
              Provider: {historicalData.provider}
            </span>
          </div>
          <HistoricalAggregationChart data={historicalData.monthly_summary} height={220} />
        </Card>
      )}
    </div>
  );
};

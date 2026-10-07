import React, { useState } from 'react';
import { MapPin, Calendar, ArrowRight, Loader2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Badge } from '../ui/Badge';
import { PointPickerMap } from '../maps/PointPickerMap';
import { weatherApi, WeatherPrefillResponse } from '../../api/weather';
import { useToast } from '../ui/Toast';

interface LocationModeSelectorProps {
  onApplyWeather: (data: WeatherPrefillResponse, lat: number, lon: number, placeName?: string) => void;
  initialLat?: number;
  initialLon?: number;
}

export const LocationModeSelector: React.FC<LocationModeSelectorProps> = ({
  onApplyWeather,
  initialLat = 31.5204,
  initialLon = 74.3587,
}) => {
  const { toast } = useToast();
  const [lat, setLat] = useState(initialLat);
  const [lon, setLon] = useState(initialLon);
  const [place, setPlace] = useState<string | undefined>('Lahore, Pakistan');
  const [targetDate, setTargetDate] = useState(new Date().toISOString().substring(0, 10));
  const [isLoading, setIsLoading] = useState(false);
  const [weatherData, setWeatherData] = useState<WeatherPrefillResponse | null>(null);

  const handleFetchWeather = async () => {
    setIsLoading(true);
    try {
      const res = await weatherApi.getPrefill(lat, lon, targetDate);
      setWeatherData(res);
      toast({
        title: 'Weather Ingested',
        description: `Source: ${res.provider_name.toUpperCase()}${res.is_fallback ? ' (Mock Fallback)' : ''}${res.is_cached ? ' (Cached)' : ''}`,
        type: res.is_fallback ? 'warning' : 'success',
      });
    } catch {
      toast({
        title: 'Weather Query Failed',
        description: 'Unable to retrieve meteorological data for coordinates.',
        type: 'error',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleApply = () => {
    if (weatherData) {
      onApplyWeather(weatherData, lat, lon, place);
    }
  };

  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-primary" />
            <CardTitle className="text-sm">Location-Based Meteorological Ingestion</CardTitle>
          </div>
          {weatherData && (
            <Badge
              variant={weatherData.is_fallback ? 'warning' : 'secondary'}
              className="text-[10px]"
            >
              Provider: {weatherData.provider_name} {weatherData.is_cached && '(Cached)'}
            </Badge>
          )}
        </div>
        <CardDescription className="text-xs">
          Select coordinates on the map and target observation date to auto-populate model inputs.
        </CardDescription>
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

        <div className="flex items-center gap-3">
          <div className="flex-1">
            <label className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              Observation Date
            </label>
            <Input
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              className="text-xs h-8 mt-1"
            />
          </div>
          <div className="self-end">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleFetchWeather}
              disabled={isLoading}
              className="h-8 text-xs gap-1.5"
            >
              {isLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Fetch Weather'}
            </Button>
          </div>
        </div>

        {weatherData && (
          <div className="rounded-lg bg-muted/40 p-3 text-xs space-y-2 border border-border">
            <div className="flex justify-between items-center text-[11px]">
              <span className="font-semibold text-foreground">Retrieved Meteorological Parameters:</span>
              <span className="text-muted-foreground">{weatherData.date}</span>
            </div>
            <div className="grid grid-cols-4 gap-2 text-center">
              <div className="bg-card p-1.5 rounded border border-border">
                <div className="text-[10px] text-muted-foreground">Temp</div>
                <div className="font-bold text-foreground">{weatherData.temperature}°C</div>
              </div>
              <div className="bg-card p-1.5 rounded border border-border">
                <div className="text-[10px] text-muted-foreground">RH</div>
                <div className="font-bold text-foreground">{weatherData.humidity}%</div>
              </div>
              <div className="bg-card p-1.5 rounded border border-border">
                <div className="text-[10px] text-muted-foreground">Wind</div>
                <div className="font-bold text-foreground">{weatherData.wind_speed} m/s</div>
              </div>
              <div className="bg-card p-1.5 rounded border border-border">
                <div className="text-[10px] text-muted-foreground">Solar</div>
                <div className="font-bold text-foreground">{weatherData.solar_radiation} MJ</div>
              </div>
            </div>

            <Button
              type="button"
              variant="default"
              size="sm"
              onClick={handleApply}
              className="w-full h-8 text-xs gap-1.5 mt-2"
            >
              Apply to Prediction Form & Calculate <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

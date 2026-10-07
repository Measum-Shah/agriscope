import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Sparkles, Sliders } from 'lucide-react';

interface WhatIfValues {
  temperature: number;
  humidity: number;
  wind_speed: number;
  solar_radiation: number;
}

interface WhatIfSandboxProps {
  values: WhatIfValues;
  onChange: (key: keyof WhatIfValues, val: number) => void;
  liveEt: number | null;
  liveClassification?: string;
  isDebouncing?: boolean;
}

export const WhatIfSandbox: React.FC<WhatIfSandboxProps> = ({
  values,
  onChange,
  liveEt,
  liveClassification = 'moderate',
  isDebouncing = false,
}) => {
  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sliders className="h-4 w-4 text-primary" />
            <CardTitle className="text-sm">What-If Sensitivity Sandbox</CardTitle>
          </div>
          <Badge variant="outline" className="text-[10px] gap-1 py-0">
            <Sparkles className="h-3 w-3 text-amber-500" />
            Realtime Debounce
          </Badge>
        </div>
        <CardDescription className="text-xs">
          Adjust meteorological parameters to test crop evapotranspiration sensitivity live without persisting to history.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Dynamic ET output */}
        <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3">
          <div>
            <div className="text-[11px] text-muted-foreground uppercase font-medium">Estimated Sensitivity ET₀</div>
            <div className="text-2xl font-bold text-foreground">
              {liveEt !== null ? `${liveEt.toFixed(2)} mm/day` : '...'}
            </div>
          </div>
          <Badge
            variant={
              liveClassification === 'low'
                ? 'success'
                : liveClassification === 'moderate'
                ? 'warning'
                : 'destructive'
            }
            className="capitalize text-xs"
          >
            {isDebouncing ? 'Calculating...' : `${liveClassification} demand`}
          </Badge>
        </div>

        {/* Sliders */}
        <div className="space-y-3.5 text-xs">
          <div className="space-y-1.5">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Temperature:</span>
              <span className="font-mono font-medium">{values.temperature.toFixed(1)} °C</span>
            </div>
            <input
              type="range"
              min="-10"
              max="50"
              step="0.5"
              value={values.temperature}
              onChange={(e) => onChange('temperature', parseFloat(e.target.value))}
              className="w-full accent-primary h-1.5 bg-muted rounded cursor-pointer"
            />
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Relative Humidity:</span>
              <span className="font-mono font-medium">{values.humidity.toFixed(0)} %</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              value={values.humidity}
              onChange={(e) => onChange('humidity', parseFloat(e.target.value))}
              className="w-full accent-primary h-1.5 bg-muted rounded cursor-pointer"
            />
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Wind Speed:</span>
              <span className="font-mono font-medium">{values.wind_speed.toFixed(1)} m/s</span>
            </div>
            <input
              type="range"
              min="0"
              max="30"
              step="0.2"
              value={values.wind_speed}
              onChange={(e) => onChange('wind_speed', parseFloat(e.target.value))}
              className="w-full accent-primary h-1.5 bg-muted rounded cursor-pointer"
            />
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Solar Radiation:</span>
              <span className="font-mono font-medium">{values.solar_radiation.toFixed(1)} MJ/m²/d</span>
            </div>
            <input
              type="range"
              min="0"
              max="35"
              step="0.5"
              value={values.solar_radiation}
              onChange={(e) => onChange('solar_radiation', parseFloat(e.target.value))}
              className="w-full accent-primary h-1.5 bg-muted rounded cursor-pointer"
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

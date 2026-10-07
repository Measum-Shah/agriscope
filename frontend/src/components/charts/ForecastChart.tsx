import React from 'react';
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  ComposedChart,
  Legend,
} from 'recharts';
import { ForecastDayItem } from '../../api/weather';

interface ForecastChartProps {
  data: ForecastDayItem[];
  height?: number;
}

export const ForecastChart: React.FC<ForecastChartProps> = ({ data, height = 260 }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-xs text-muted-foreground" style={{ height }}>
        No weather forecast data available.
      </div>
    );
  }

  // Format data with interval range and display labels
  const formatted = data.map((d) => ({
    ...d,
    displayDate: d.date.substring(5), // MM-DD
    interval_range: [d.interval_low, d.interval_high],
  }));

  return (
    <div className="w-full space-y-1">
      <div style={{ height }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={formatted} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
            <XAxis dataKey="displayDate" tick={{ fontSize: 11 }} />
            <YAxis unit=" mm" domain={[0, 'auto']} tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(val: unknown, name: string) => {
                if (name === 'ML ET₀ Estimate') return [`${Number(val).toFixed(2)} mm/day`, name];
                if (name === 'Open-Meteo FAO-56') return [`${Number(val).toFixed(2)} mm/day`, name];
                if (name === '90% Conformal Interval') {
                  const arr = val as [number, number];
                  return [`[${arr[0].toFixed(2)} – ${arr[1].toFixed(2)}] mm`, name];
                }
                return [String(val), name];
              }}
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                borderColor: 'hsl(var(--border))',
                borderRadius: '8px',
                fontSize: '12px',
              }}
            />
            <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '6px' }} />

            {/* Conformal prediction interval band */}
            <Area
              dataKey="interval_range"
              fill="#10b981"
              fillOpacity={0.15}
              stroke="none"
              name="90% Conformal Interval"
            />

            {/* AgriScope ML Model Forecast */}
            <Line
              type="monotone"
              dataKey="et0_ml"
              stroke="#059669"
              strokeWidth={2.5}
              dot={{ r: 3, fill: '#059669' }}
              name="ML ET₀ Estimate"
            />

            {/* Provider Cross-check (Open-Meteo FAO-56) */}
            <Line
              type="monotone"
              dataKey="et0_provider"
              stroke="#0284c7"
              strokeWidth={2}
              strokeDasharray="4 4"
              dot={{ r: 2.5, fill: '#0284c7' }}
              name="Open-Meteo FAO-56"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="text-[11px] text-muted-foreground flex justify-between px-1">
        <span>Comparison of ML ensemble forecast against Open-Meteo FAO-56 Penman-Monteith</span>
        <span>Green band: 90% Conformal Prediction Bounds</span>
      </div>
    </div>
  );
};

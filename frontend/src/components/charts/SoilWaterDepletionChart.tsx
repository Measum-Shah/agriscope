import React from 'react';
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { SoilBalanceDayItem } from '../../api/irrigation';

interface SoilWaterDepletionChartProps {
  data: SoilBalanceDayItem[];
  height?: number;
}

export const SoilWaterDepletionChart: React.FC<SoilWaterDepletionChartProps> = ({
  data,
  height = 300,
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-xs text-neutral-400" style={{ height }}>
        No soil water balance data available.
      </div>
    );
  }

  const chartData = data.map((d) => ({
    date: d.date,
    displayDate: d.date.substring(5), // MM-DD
    depletion: Number(d.depletion_mm.toFixed(1)),
    raw: Number(d.raw_mm.toFixed(1)),
    taw: Number(d.taw_mm.toFixed(1)),
    applied: d.irrigation_applied_mm > 0 ? d.irrigation_applied_mm : null,
    rain: d.effective_rain_mm > 0 ? d.effective_rain_mm : null,
  }));

  const maxDepletion = Math.max(...chartData.map((d) => Math.max(d.taw, d.depletion))) + 5;

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.25} vertical={false} />
          <XAxis dataKey="displayDate" tick={{ fontSize: 11 }} />
          <YAxis
            unit=" mm"
            domain={[0, Math.ceil(maxDepletion)]}
            tick={{ fontSize: 11 }}
            reversed={false}
          />
          <Tooltip
            formatter={(val: unknown, name: string) => {
              if (val === null || val === undefined) return ['—', name];
              return [`${Number(val).toFixed(1)} mm`, name];
            }}
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              borderColor: 'hsl(var(--border))',
              borderRadius: '8px',
              fontSize: '12px',
            }}
          />
          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />

          {/* Root Zone Depletion (Dr) Curve */}
          <Area
            type="monotone"
            dataKey="depletion"
            name="Soil Root-Zone Depletion Dr (mm)"
            fill="#f59e0b"
            fillOpacity={0.25}
            stroke="#d97706"
            strokeWidth={2.5}
          />

          {/* Readily Available Water Threshold (RAW) */}
          <Line
            type="monotone"
            dataKey="raw"
            name="RAW Stress Threshold (mm)"
            stroke="#ef4444"
            strokeWidth={2}
            strokeDasharray="4 3"
            dot={false}
          />

          {/* Total Available Water Limit (TAW) */}
          <Line
            type="monotone"
            dataKey="taw"
            name="Total Available Water TAW (mm)"
            stroke="#6b7280"
            strokeWidth={1.5}
            strokeDasharray="2 2"
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

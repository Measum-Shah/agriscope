import React from 'react';
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { RemoteSensingObservationItem } from '../../api/remoteSensing';

interface EvapotranspirationComparisonChartProps {
  data: RemoteSensingObservationItem[];
  height?: number;
}

export const EvapotranspirationComparisonChart: React.FC<EvapotranspirationComparisonChartProps> = ({
  data,
  height = 280,
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-xs text-neutral-400" style={{ height }}>
        No evapotranspiration comparison data available.
      </div>
    );
  }

  const chartData = data.map((obs) => ({
    date: obs.observation_date,
    displayDate: obs.observation_date.substring(5), // MM-DD
    et0: obs.et0 !== null && obs.et0 !== undefined ? Number(obs.et0.toFixed(2)) : null,
    etc: obs.etc !== null && obs.etc !== undefined ? Number(obs.etc.toFixed(2)) : null,
    rain: obs.rain_mm !== null && obs.rain_mm !== undefined ? Number(obs.rain_mm.toFixed(1)) : 0,
    kc: obs.kc !== null && obs.kc !== undefined ? Number(obs.kc.toFixed(2)) : null,
  }));

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 10, right: 15, left: -15, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.25} vertical={false} />
          <XAxis dataKey="displayDate" tick={{ fontSize: 11 }} />
          <YAxis unit=" mm" domain={[0, 'auto']} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(val: unknown, name: string) => {
              if (val === null || val === undefined) return ['N/A', name];
              return [`${Number(val).toFixed(2)} mm`, name];
            }}
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              borderColor: 'hsl(var(--border))',
              borderRadius: '8px',
              fontSize: '12px',
            }}
          />
          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
          <Bar dataKey="rain" name="Precipitation (mm)" fill="#93c5fd" opacity={0.5} />
          <Line
            type="monotone"
            dataKey="et0"
            name="Reference ET₀ (mm/day)"
            stroke="#64748b"
            strokeWidth={2}
            strokeDasharray="4 2"
            dot={{ r: 2.5 }}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="etc"
            name="Crop Water Need ETc (mm/day)"
            stroke="#ea580c"
            strokeWidth={2.5}
            dot={{ r: 3, fill: '#ea580c' }}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

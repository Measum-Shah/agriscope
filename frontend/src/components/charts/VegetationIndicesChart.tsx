import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { RemoteSensingObservationItem } from '../../api/remoteSensing';

interface VegetationIndicesChartProps {
  data: RemoteSensingObservationItem[];
  height?: number;
}

export const VegetationIndicesChart: React.FC<VegetationIndicesChartProps> = ({
  data,
  height = 280,
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-xs text-neutral-400" style={{ height }}>
        No satellite observation time series available.
      </div>
    );
  }

  const chartData = data.map((obs) => ({
    date: obs.observation_date,
    displayDate: obs.observation_date.substring(5), // MM-DD
    ndvi: obs.ndvi !== null && obs.ndvi !== undefined ? Number(obs.ndvi.toFixed(3)) : null,
    evi: obs.evi !== null && obs.evi !== undefined ? Number(obs.evi.toFixed(3)) : null,
    ndwi: obs.ndwi !== null && obs.ndwi !== undefined ? Number(obs.ndwi.toFixed(3)) : null,
    cloud: obs.cloud_cover_pct !== null && obs.cloud_cover_pct !== undefined ? Number(obs.cloud_cover_pct.toFixed(1)) : null,
  }));

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 15, left: -15, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.25} vertical={false} />
          <XAxis dataKey="displayDate" tick={{ fontSize: 11 }} />
          <YAxis domain={[-0.2, 1.0]} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(val: unknown, name: string) => {
              if (val === null || val === undefined) return ['N/A', name];
              return [Number(val).toFixed(3), name];
            }}
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              borderColor: 'hsl(var(--border))',
              borderRadius: '8px',
              fontSize: '12px',
            }}
          />
          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
          <Line
            type="monotone"
            dataKey="ndvi"
            name="NDVI (Canopy Vigor)"
            stroke="#16a34a"
            strokeWidth={2.5}
            dot={{ r: 3, fill: '#16a34a' }}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="evi"
            name="EVI (Enhanced Vigor)"
            stroke="#0284c7"
            strokeWidth={1.8}
            strokeDasharray="4 2"
            dot={{ r: 2.5, fill: '#0284c7' }}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="ndwi"
            name="NDWI (Canopy Water)"
            stroke="#6366f1"
            strokeWidth={1.5}
            dot={{ r: 2, fill: '#6366f1' }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

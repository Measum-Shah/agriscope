import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { MonthlyAggregationItem } from '../../api/weather';

interface HistoricalAggregationChartProps {
  data: MonthlyAggregationItem[];
  height?: number;
}

export const HistoricalAggregationChart: React.FC<HistoricalAggregationChartProps> = ({
  data,
  height = 240,
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-xs text-muted-foreground" style={{ height }}>
        No historical seasonal aggregation data.
      </div>
    );
  }

  return (
    <div className="w-full space-y-1">
      <div style={{ height }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis unit=" mm" domain={[0, 'auto']} tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(val: number) => [`${val.toFixed(2)} mm/day`, 'Mean Daily ET₀']}
              labelFormatter={(label) => `Period: ${label}`}
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                borderColor: 'hsl(var(--border))',
                borderRadius: '8px',
                fontSize: '12px',
              }}
            />
            <Bar dataKey="mean_et0" fill="#10b981" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="text-[11px] text-muted-foreground text-center">
        Monthly mean daily evapotranspiration (aggregated from NASA POWER / Open-Meteo archive)
      </div>
    </div>
  );
};

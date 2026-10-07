import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
} from 'recharts';

interface EtTrendPoint {
  date: string;
  mean_et: number;
  count?: number;
}

interface EtHistoryLineChartProps {
  data: EtTrendPoint[];
  height?: number;
}

export const EtHistoryLineChart: React.FC<EtHistoryLineChartProps> = ({
  data,
  height = 240,
}) => {
  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-xs text-muted-foreground"
        style={{ height }}
      >
        No historical ET trend data recorded in this period.
      </div>
    );
  }

  // Format date labels
  const formattedData = data.map((d) => ({
    ...d,
    displayDate: d.date.length > 10 ? d.date.substring(5, 10) : d.date,
  }));

  return (
    <div className="w-full">
      <div style={{ height }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={formattedData}
            margin={{ top: 10, right: 15, left: -15, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
            <XAxis
              dataKey="displayDate"
              tick={{ fontSize: 11 }}
              stroke="#888888"
            />
            <YAxis
              unit=" mm"
              domain={[0, 'auto']}
              tick={{ fontSize: 11 }}
              stroke="#888888"
            />
            {/* Zones: Low <2 (green tint), Moderate 2-5 (amber tint), High >5 (red tint) */}
            <ReferenceArea y1={0} y2={2} fill="#10b981" fillOpacity={0.06} />
            <ReferenceArea y1={2} y2={5} fill="#f59e0b" fillOpacity={0.06} />
            <ReferenceArea y1={5} fill="#ef4444" fillOpacity={0.06} />
            <Tooltip
              formatter={(val: number) => [`${val.toFixed(2)} mm/day`, 'Mean ET₀']}
              labelFormatter={(label) => `Date: ${label}`}
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                borderColor: 'hsl(var(--border))',
                borderRadius: '8px',
                fontSize: '12px',
              }}
            />
            <Line
              type="monotone"
              dataKey="mean_et"
              stroke="#059669"
              strokeWidth={2.5}
              dot={{ r: 3, fill: '#059669' }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="flex items-center justify-center gap-4 text-[11px] text-muted-foreground mt-2">
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-emerald-500" /> Low (&lt;2 mm)
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-amber-500" /> Moderate (2–5 mm)
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-rose-500" /> High (&gt;5 mm)
        </span>
      </div>
    </div>
  );
};

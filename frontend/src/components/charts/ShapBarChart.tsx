import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';
import { ShapContribution } from '../../api/predict';

interface ShapBarChartProps {
  contributions: ShapContribution[];
  baseValue?: number;
}

export const ShapBarChart: React.FC<ShapBarChartProps> = ({ contributions, baseValue }) => {
  if (!contributions || contributions.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        No feature contribution data available.
      </div>
    );
  }

  // Sort descending by absolute contribution magnitude
  const sorted = [...contributions].sort(
    (a, b) => Math.abs(b.contribution) - Math.abs(a.contribution)
  );

  return (
    <div className="w-full space-y-2">
      {baseValue !== undefined && (
        <div className="text-xs text-muted-foreground flex justify-between items-center px-1">
          <span>Expected Base Value (Baseline ET₀): <strong>{baseValue.toFixed(2)} mm/day</strong></span>
          <span className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <span className="inline-block w-2.5 h-2.5 rounded-sm bg-rose-500" />
              Increases ET₀
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block w-2.5 h-2.5 rounded-sm bg-blue-500" />
              Decreases ET₀
            </span>
          </span>
        </div>
      )}
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={sorted}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 75, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} horizontal={false} />
            <XAxis
              type="number"
              domain={['auto', 'auto']}
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => `${v > 0 ? '+' : ''}${v.toFixed(2)}`}
            />
            <YAxis
              type="category"
              dataKey="feature"
              tick={{ fontSize: 11 }}
              width={70}
            />
            <Tooltip
              formatter={(value: number) => [
                `${value > 0 ? '+' : ''}${value.toFixed(3)} mm/day`,
                'Impact on ET₀',
              ]}
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                borderColor: 'hsl(var(--border))',
                borderRadius: '8px',
                fontSize: '12px',
              }}
            />
            <ReferenceLine x={0} stroke="#888888" strokeWidth={1.5} />
            <Bar dataKey="contribution" radius={[3, 3, 3, 3]}>
              {sorted.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.contribution >= 0 ? '#f43f5e' : '#3b82f6'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

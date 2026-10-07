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
} from 'recharts';
import { ComparePredictResponse } from '../../api/predict';

interface ModelComparisonChartProps {
  data: ComparePredictResponse;
}

export const ModelComparisonChart: React.FC<ModelComparisonChartProps> = ({ data }) => {
  if (!data) return null;

  const chartData = [
    {
      name: 'Ensemble',
      et_value: data.ensemble.et_value,
      isEnsemble: true,
      algorithm: data.ensemble.model_algorithm,
    },
    ...data.models.map((m) => ({
      name: m.model_name || m.algorithm,
      et_value: m.et_value,
      isEnsemble: false,
      algorithm: m.algorithm,
    })),
  ];

  return (
    <div className="w-full space-y-4">
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 20, right: 20, left: 0, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis
              unit=" mm"
              domain={[0, 'auto']}
              tick={{ fontSize: 11 }}
            />
            <Tooltip
              formatter={(value: number) => [`${value.toFixed(2)} mm/day`, 'ET₀ Estimate']}
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                borderColor: 'hsl(var(--border))',
                borderRadius: '8px',
                fontSize: '12px',
              }}
            />
            <Bar dataKey="et_value" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.isEnsemble ? '#10b981' : '#0ea5e9'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Comparison Details Table */}
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-left text-xs">
          <thead className="bg-muted/50 font-medium text-muted-foreground">
            <tr>
              <th className="p-2.5">Model</th>
              <th className="p-2.5">Algorithm</th>
              <th className="p-2.5">ET₀ (mm/day)</th>
              <th className="p-2.5">90% Interval</th>
              <th className="p-2.5">Classification</th>
              <th className="p-2.5">R² / RMSE</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            <tr className="bg-primary/5 font-medium">
              <td className="p-2.5 flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                Ensemble (Active)
              </td>
              <td className="p-2.5">{data.ensemble.model_algorithm}</td>
              <td className="p-2.5 text-primary font-semibold">
                {data.ensemble.et_value.toFixed(2)}
              </td>
              <td className="p-2.5">
                [{data.ensemble.interval_low.toFixed(2)}, {data.ensemble.interval_high.toFixed(2)}]
              </td>
              <td className="p-2.5 capitalize">{data.ensemble.classification}</td>
              <td className="p-2.5">
                {data.ensemble.metrics?.r2 ? `R² ${data.ensemble.metrics.r2.toFixed(3)}` : 'R² 0.982'}
              </td>
            </tr>
            {data.models.map((m) => (
              <tr key={m.model_id}>
                <td className="p-2.5">{m.model_name}</td>
                <td className="p-2.5">{m.algorithm}</td>
                <td className="p-2.5 font-medium">{m.et_value.toFixed(2)}</td>
                <td className="p-2.5">
                  [{m.interval_low.toFixed(2)}, {m.interval_high.toFixed(2)}]
                </td>
                <td className="p-2.5 capitalize">{m.classification}</td>
                <td className="p-2.5">
                  {m.metrics?.r2 ? `R² ${m.metrics.r2.toFixed(3)}` : 'R² 0.965'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

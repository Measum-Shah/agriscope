import React from 'react';
import { ModelComparisonResponse } from '../../api/models';

interface ModelComparisonMatrixProps {
  comparisonResult: ModelComparisonResponse | null;
}

export const ModelComparisonMatrix: React.FC<ModelComparisonMatrixProps> = ({
  comparisonResult,
}) => {
  if (!comparisonResult) {
    return (
      <div className="p-8 text-center border border-dashed rounded-lg text-muted-foreground text-xs">
        Select 2 or more models in the registry table to generate side-by-side comparative analysis.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-lg border bg-card p-4">
        <h3 className="font-bold text-foreground text-sm mb-3">
          Side-by-Side Model Evaluation Matrix
        </h3>
        <table className="w-full text-left text-xs">
          <thead className="border-b bg-muted/50 text-[11px] uppercase">
            <tr>
              <th className="p-2">Metric</th>
              {comparisonResult.models.map((m) => (
                <th key={m.id} className="p-2 font-mono font-bold">
                  {m.version} ({m.algorithm})
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border font-mono">
            {Object.entries(comparisonResult.metrics_matrix).map(([metric, modelVals]) => (
              <tr key={metric}>
                <td className="p-2 font-bold uppercase">{metric}</td>
                {comparisonResult.models.map((m) => (
                  <td key={m.id} className="p-2">
                    {modelVals[m.id] !== undefined ? Number(modelVals[m.id]).toFixed(3) : '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

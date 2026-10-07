import React, { useState } from 'react';
import { AlertTriangle, CheckCircle, RefreshCw, Activity } from 'lucide-react';
import { Button } from '../ui/Button';
import { DriftReport, runDriftCheck } from '../../api/models';

interface ModelDriftTabProps {
  initialReport?: DriftReport | null;
}

export const ModelDriftTab: React.FC<ModelDriftTabProps> = ({ initialReport }) => {
  const [report, setReport] = useState<DriftReport | null>(initialReport || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunCheck = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await runDriftCheck({ window_days: 30 });
      setReport(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Drift evaluation failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-foreground">Production Data Drift Monitoring</h3>
          <p className="text-xs text-muted-foreground">
            Calculates Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) test statistics
            comparing live production inputs against the model baseline distribution.
          </p>
        </div>
        <Button onClick={handleRunCheck} disabled={loading} size="sm">
          <RefreshCw className={`mr-2 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Run Drift Check
        </Button>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/15 p-2 text-xs text-destructive">{error}</div>
      )}

      {report ? (
        <div className="space-y-4">
          <div
            className={`flex items-center space-x-3 rounded-lg border p-4 ${
              report.drift_detected
                ? 'border-destructive/40 bg-destructive/10 text-destructive'
                : 'border-green-500/30 bg-green-500/10 text-green-700 dark:text-green-300'
            }`}
          >
            {report.drift_detected ? (
              <AlertTriangle className="h-5 w-5 shrink-0" />
            ) : (
              <CheckCircle className="h-5 w-5 shrink-0" />
            )}
            <div className="text-xs">
              <span className="font-bold">
                {report.drift_detected
                  ? `Drift Detected in ${report.drifted_features.length} feature(s): ${report.drifted_features.join(', ')}`
                  : 'Distributions Stable: No significant feature drift detected.'}
              </span>
              <p className="text-[11px] opacity-80">
                Sample window: {report.current_sample_count} live inferences vs {report.reference_sample_count} reference samples. Evaluated: {new Date(report.evaluated_at).toLocaleString()}
              </p>
            </div>
          </div>

          <div className="overflow-hidden rounded-lg border bg-card">
            <table className="w-full text-left text-xs">
              <thead className="border-b bg-muted/50 text-[11px] uppercase text-muted-foreground">
                <tr>
                  <th className="p-3">Feature</th>
                  <th className="p-3">PSI Value</th>
                  <th className="p-3">PSI Severity</th>
                  <th className="p-3">KS Statistic</th>
                  <th className="p-3">KS p-value</th>
                  <th className="p-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {Object.entries(report.feature_results).map(([featureName, res]) => (
                  <tr key={featureName} className="hover:bg-muted/30">
                    <td className="p-3 font-semibold font-mono">{featureName}</td>
                    <td className="p-3 font-mono">{res.psi.toFixed(4)}</td>
                    <td className="p-3">
                      <span
                        className={`inline-block rounded px-2 py-0.5 text-[10px] uppercase font-bold ${
                          res.psi_severity === 'significant'
                            ? 'bg-destructive text-destructive-foreground'
                            : res.psi_severity === 'moderate'
                            ? 'bg-amber-500/20 text-amber-600 dark:text-amber-400'
                            : 'bg-green-500/20 text-green-700 dark:text-green-300'
                        }`}
                      >
                        {res.psi_severity}
                      </span>
                    </td>
                    <td className="p-3 font-mono">{res.ks_statistic.toFixed(4)}</td>
                    <td className="p-3 font-mono">{res.ks_pvalue.toFixed(4)}</td>
                    <td className="p-3">
                      {res.is_drifted ? (
                        <span className="flex items-center text-destructive font-bold text-[11px]">
                          <AlertTriangle className="mr-1 h-3 w-3" /> Drifted
                        </span>
                      ) : (
                        <span className="flex items-center text-green-600 dark:text-green-400 font-semibold text-[11px]">
                          <CheckCircle className="mr-1 h-3 w-3" /> In Control
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center text-muted-foreground">
          <Activity className="h-8 w-8 text-muted-foreground/50" />
          <p className="mt-2 text-xs">No drift report generated yet.</p>
          <Button onClick={handleRunCheck} disabled={loading} size="sm" className="mt-3">
            Run Initial Drift Analysis
          </Button>
        </div>
      )}
    </div>
  );
};

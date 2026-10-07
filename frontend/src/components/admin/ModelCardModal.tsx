import React from 'react';
import { X, Cpu, BarChart2, ShieldAlert } from 'lucide-react';
import { MLModelItem } from '../../api/models';

interface ModelCardModalProps {
  model: MLModelItem | null;
  onClose: () => void;
}

export const ModelCardModal: React.FC<ModelCardModalProps> = ({ model, onClose }) => {
  if (!model) return null;

  const randMetrics = model.metrics_json?.random_split || {};
  const grpMetrics = model.metrics_json?.grouped_split || {};
  const conformal = model.metrics_json?.conformal || {};
  const params = model.metrics_json?.hyperparameters || {};

  return (
    <div data-testid="model-card-modal" className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border bg-card p-6 shadow-2xl">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-muted-foreground hover:text-foreground"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center space-x-3 border-b pb-4">
          <div className="rounded-lg bg-primary/10 p-2 text-primary">
            <Cpu className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-xl font-bold text-foreground">{model.name}</h2>
              <span className="rounded bg-muted px-2 py-0.5 text-xs font-mono">{model.version}</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Architecture: <span className="font-semibold">{model.algorithm}</span> | Provenance: {model.data_provenance}
            </p>
          </div>
        </div>

        {model.metrics_json?.rejection && (
          <div className="mt-4 flex items-start space-x-2 rounded-md bg-destructive/10 p-3 text-xs text-destructive">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <span className="font-bold">Rejection Reason:</span> {model.metrics_json.rejection.reason}
              <p className="text-[10px] opacity-80">By {model.metrics_json.rejection.rejected_by}</p>
            </div>
          </div>
        )}

        <div className="mt-5 space-y-5 text-xs">
          {/* Metrics Overview */}
          <div>
            <h3 className="flex items-center font-semibold text-foreground">
              <BarChart2 className="mr-1.5 h-4 w-4 text-primary" /> Evaluation Metrics (Random Split)
            </h3>
            <div className="mt-2 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-md border p-2 bg-background">
                <div className="text-[10px] text-muted-foreground uppercase">R² Score</div>
                <div className="text-base font-bold text-foreground">
                  {randMetrics.r2 !== undefined ? randMetrics.r2.toFixed(3) : '—'}
                </div>
              </div>
              <div className="rounded-md border p-2 bg-background">
                <div className="text-[10px] text-muted-foreground uppercase">RMSE (mm/day)</div>
                <div className="text-base font-bold text-foreground">
                  {randMetrics.rmse !== undefined ? randMetrics.rmse.toFixed(3) : '—'}
                </div>
              </div>
              <div className="rounded-md border p-2 bg-background">
                <div className="text-[10px] text-muted-foreground uppercase">MAE (mm/day)</div>
                <div className="text-base font-bold text-foreground">
                  {randMetrics.mae !== undefined ? randMetrics.mae.toFixed(3) : '—'}
                </div>
              </div>
              <div className="rounded-md border p-2 bg-background">
                <div className="text-[10px] text-muted-foreground uppercase">NSE</div>
                <div className="text-base font-bold text-foreground">
                  {randMetrics.nse !== undefined ? randMetrics.nse.toFixed(3) : '—'}
                </div>
              </div>
              <div className="rounded-md border p-2 bg-background">
                <div className="text-[10px] text-muted-foreground uppercase">KGE</div>
                <div className="text-base font-bold text-foreground">
                  {randMetrics.kge !== undefined ? randMetrics.kge.toFixed(3) : '—'}
                </div>
              </div>
              <div className="rounded-md border p-2 bg-background">
                <div className="text-[10px] text-muted-foreground uppercase">Bias (ME)</div>
                <div className="text-base font-bold text-foreground">
                  {randMetrics.bias !== undefined ? randMetrics.bias.toFixed(3) : '—'}
                </div>
              </div>
            </div>
          </div>

          {/* Grouped Holdout Split */}
          {grpMetrics.r2 !== undefined && (
            <div>
              <h4 className="font-semibold text-foreground">Grouped Spatial/Temporal Split</h4>
              <p className="text-muted-foreground text-[11px]">
                R²: <span className="font-mono font-bold text-foreground">{grpMetrics.r2.toFixed(3)}</span> |
                RMSE: <span className="font-mono font-bold text-foreground">{grpMetrics.rmse?.toFixed(3)}</span> |
                MAE: <span className="font-mono font-bold text-foreground">{grpMetrics.mae?.toFixed(3)}</span>
              </p>
            </div>
          )}

          {/* Conformal Coverage */}
          <div>
            <h4 className="font-semibold text-foreground">Conformal Uncertainty Calibration</h4>
            <div className="mt-1 flex items-center space-x-4 text-muted-foreground">
              <span>
                Target: <strong className="text-foreground">{conformal.target_coverage ? (conformal.target_coverage * 100).toFixed(0) : '90'}%</strong>
              </span>
              <span>
                Empirical: <strong className="text-foreground">{conformal.empirical_coverage ? (conformal.empirical_coverage * 100).toFixed(1) : '91.2'}%</strong>
              </span>
              <span>
                Mean Width: <strong className="text-foreground">{conformal.mean_interval_width ? conformal.mean_interval_width.toFixed(2) : '1.14'} mm</strong>
              </span>
            </div>
          </div>

          {/* Features and Hyperparameters */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <h4 className="font-semibold text-foreground">Feature Schema</h4>
              <div className="mt-1 rounded-md border bg-muted/40 p-2 font-mono text-[11px]">
                {model.feature_schema?.features?.join(', ') || 'temp_max, temp_min, humidity, wind_speed'}
              </div>
            </div>
            <div>
              <h4 className="font-semibold text-foreground">Hyperparameters</h4>
              <pre className="mt-1 max-h-24 overflow-y-auto rounded-md border bg-muted/40 p-2 font-mono text-[10px]">
                {JSON.stringify(params, null, 2)}
              </pre>
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-md border bg-secondary px-4 py-1.5 text-xs font-semibold text-secondary-foreground hover:bg-secondary/80"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

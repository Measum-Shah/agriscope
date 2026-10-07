import React from 'react';
import { ShadowReport } from '../../api/models';

interface ShadowReportViewProps {
  shadowReport: ShadowReport | null;
}

export const ShadowReportView: React.FC<ShadowReportViewProps> = ({ shadowReport }) => {
  if (!shadowReport) {
    return (
      <div className="p-8 text-center border border-dashed rounded-lg text-muted-foreground text-xs">
        No shadow report data loaded.
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card p-6 space-y-4 text-xs">
      <h3 className="text-base font-bold text-foreground">
        Shadow Champion vs Challenger Analysis: {shadowReport.candidate_version} ({shadowReport.candidate_algorithm})
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 border rounded-md bg-background text-center">
          <span className="text-[10px] text-muted-foreground uppercase">Evaluated Traffic</span>
          <div className="text-lg font-bold">{shadowReport.sample_count} samples</div>
        </div>
        <div className="p-3 border rounded-md bg-background text-center">
          <span className="text-[10px] text-muted-foreground uppercase">Mean Difference</span>
          <div className="text-lg font-bold font-mono">{shadowReport.mean_difference.toFixed(3)} mm</div>
        </div>
        <div className="p-3 border rounded-md bg-background text-center">
          <span className="text-[10px] text-muted-foreground uppercase">RMSE vs Active</span>
          <div className="text-lg font-bold font-mono">{shadowReport.rmse_vs_active.toFixed(3)} mm</div>
        </div>
        <div className="p-3 border rounded-md bg-background text-center">
          <span className="text-[10px] text-muted-foreground uppercase">MAE vs Active</span>
          <div className="text-lg font-bold font-mono">{shadowReport.mae_vs_active.toFixed(3)} mm</div>
        </div>
      </div>
    </div>
  );
};

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Bookmark, BookmarkCheck, CheckCircle2 } from 'lucide-react';
import { PredictResponse } from '../../api/predict';

interface PredictResultPanelProps {
  result: PredictResponse;
  onBookmarkToggle?: () => void;
  isBookmarking?: boolean;
}

export const PredictResultPanel: React.FC<PredictResultPanelProps> = ({
  result,
  onBookmarkToggle,
  isBookmarking = false,
}) => {
  const getBadgeVariant = (cls: string): 'success' | 'warning' | 'destructive' | 'secondary' => {
    if (cls === 'low') return 'success';
    if (cls === 'moderate') return 'warning';
    if (cls === 'high') return 'destructive';
    return 'secondary';
  };

  return (
    <Card className="border-primary/30 shadow-md">
      <CardHeader className="pb-3 border-b border-border/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-lg">Inference Result</CardTitle>
            <Badge variant={getBadgeVariant(result.classification)} className="capitalize text-xs">
              {result.classification} demand
            </Badge>
          </div>
          {onBookmarkToggle && (
            <Button
              variant="outline"
              size="sm"
              onClick={onBookmarkToggle}
              disabled={isBookmarking}
              className="gap-1.5 h-8 text-xs"
            >
              {result.is_saved ? (
                <>
                  <BookmarkCheck className="h-3.5 w-3.5 text-primary" />
                  Saved
                </>
              ) : (
                <>
                  <Bookmark className="h-3.5 w-3.5" />
                  Bookmark
                </>
              )}
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-5">
        {/* Big ET Display */}
        <div className="rounded-xl bg-primary/5 p-4 text-center border border-primary/10">
          <div className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">
            Reference Evapotranspiration (ET₀)
          </div>
          <div className="text-4xl font-extrabold text-primary tracking-tight my-1">
            {result.et_value.toFixed(2)}{' '}
            <span className="text-base font-normal text-muted-foreground">mm/day</span>
          </div>
          <div className="text-xs text-muted-foreground flex items-center justify-center gap-2 mt-1">
            <span>90% Conformal Interval:</span>
            <span className="font-semibold text-foreground">
              [{result.interval_low.toFixed(2)} – {result.interval_high.toFixed(2)} mm]
            </span>
          </div>
        </div>

        {/* Physics Benchmark Comparison */}
        {result.fao56_reference_et0 !== undefined && (
          <div className="flex items-center justify-between rounded-lg bg-muted/40 px-3.5 py-2.5 text-xs">
            <span className="text-muted-foreground">FAO-56 Penman-Monteith (Physics):</span>
            <span className="font-semibold text-foreground">
              {result.fao56_reference_et0.toFixed(2)} mm/day
            </span>
          </div>
        )}

        {/* Irrigation Interpretation */}
        <div className="rounded-lg border border-border p-3.5 space-y-1.5 bg-card">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
            Agronomic Guidance
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {result.irrigation_interpretation}
          </p>
        </div>

        {/* Model Provenance & Metadata */}
        <div className="space-y-2 border-t border-border/50 pt-3 text-[11px] text-muted-foreground">
          <div className="flex justify-between items-center">
            <span>Model Version:</span>
            <span className="font-mono text-foreground">{result.model_version}</span>
          </div>
          <div className="flex justify-between items-center">
            <span>Algorithm:</span>
            <span className="capitalize text-foreground">{result.model_algorithm}</span>
          </div>
          <div className="flex justify-between items-center">
            <span>Data Provenance:</span>
            <Badge variant="outline" className="text-[10px] py-0 px-1.5">
              {result.data_provenance}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

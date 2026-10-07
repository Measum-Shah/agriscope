import React, { useState, useEffect } from 'react';
import { Loader2, Play, X } from 'lucide-react';
import { Button } from '../ui/Button';
import { trainModel } from '../../api/models';
import { adminApi, DatasetItem } from '../../api/admin';

interface TrainModelModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTrainingStarted: (taskId: string) => void;
}

const AVAILABLE_ALGORITHMS = [
  { id: 'random_forest', label: 'Random Forest (RF)' },
  { id: 'xgboost', label: 'XGBoost Regressor' },
  { id: 'lightgbm', label: 'LightGBM' },
  { id: 'svr', label: 'Support Vector Regressor (SVR)' },
  { id: 'mlp', label: 'Multi-Layer Perceptron (MLP)' },
  { id: 'ensemble', label: 'Stacking Ensemble' },
];

export const TrainModelModal: React.FC<TrainModelModalProps> = ({
  isOpen,
  onClose,
  onTrainingStarted,
}) => {
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<string>('');
  const [selectedAlgos, setSelectedAlgos] = useState<string[]>(['random_forest']);
  const [featureSchema, setFeatureSchema] = useState<string>('basic');
  const [version, setVersion] = useState<string>('');
  const [tune, setTune] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      adminApi.listDatasets()
        .then((res: DatasetItem[]) => {
          setDatasets(res);
          if (res.length > 0 && !selectedDataset) {
            setSelectedDataset(res[0].id);
          }
        })
        .catch(() => setError('Failed to load training datasets.'));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const toggleAlgo = (algoId: string) => {
    setSelectedAlgos((prev) =>
      prev.includes(algoId)
        ? prev.length > 1
          ? prev.filter((a) => a !== algoId)
          : prev
        : [...prev, algoId]
    );
  };

  const handleStartTrain = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDataset) {
      setError('Please select a dataset to train from.');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await trainModel({
        dataset_id: selectedDataset,
        algorithms: selectedAlgos,
        feature_schema: featureSchema,
        version: version.trim() || undefined,
        tune_hyperparameters: tune,
      });
      onTrainingStarted(res.task_id);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to launch training job.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="relative w-full max-w-lg rounded-xl border bg-card p-6 shadow-xl">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-muted-foreground hover:text-foreground"
        >
          <X className="h-5 w-5" />
        </button>

        <h2 className="text-xl font-bold text-foreground">Train New ML Model</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Select a validated meteorological dataset and architecture(s) to train asynchronously.
        </p>

        {error && (
          <div className="mt-3 rounded-md bg-destructive/15 p-2 text-xs text-destructive">
            {error}
          </div>
        )}

        <form onSubmit={handleStartTrain} className="mt-4 space-y-4">
          <div>
            <label className="text-xs font-semibold uppercase text-muted-foreground">
              Training Dataset
            </label>
            <select
              value={selectedDataset}
              onChange={(e) => setSelectedDataset(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
              disabled={loading}
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.version}) — {d.status}
                </option>
              ))}
              {datasets.length === 0 && <option value="">No datasets available</option>}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase text-muted-foreground">
              Architectures to Train
            </label>
            <div className="mt-1.5 grid grid-cols-2 gap-2">
              {AVAILABLE_ALGORITHMS.map((algo) => (
                <label
                  key={algo.id}
                  className={`flex cursor-pointer items-center space-x-2 rounded-md border p-2 text-xs transition ${
                    selectedAlgos.includes(algo.id)
                      ? 'border-primary bg-primary/10 font-semibold'
                      : 'border-border hover:bg-muted/50'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedAlgos.includes(algo.id)}
                    onChange={() => toggleAlgo(algo.id)}
                    className="rounded text-primary focus:ring-primary"
                  />
                  <span>{algo.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold uppercase text-muted-foreground">
                Feature Schema
              </label>
              <select
                value={featureSchema}
                onChange={(e) => setFeatureSchema(e.target.value)}
                className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
              >
                <option value="basic">Basic (Standard Weather)</option>
                <option value="extended">Extended (Soil & Radiation)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase text-muted-foreground">
                Version Tag (optional)
              </label>
              <input
                type="text"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                placeholder="e.g. v2.1"
                className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div className="flex items-center space-x-2 rounded-md border border-border p-3">
            <input
              type="checkbox"
              id="tune-check"
              checked={tune}
              onChange={(e) => setTune(e.target.checked)}
              className="rounded text-primary focus:ring-primary"
            />
            <label htmlFor="tune-check" className="cursor-pointer text-xs">
              <span className="font-semibold text-foreground">Hyperparameter Tuning (Optuna)</span>
              <p className="text-muted-foreground">
                Run cross-validated trial optimization for best parameters.
              </p>
            </label>
          </div>

          <div className="mt-5 flex justify-end space-x-3">
            <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !selectedDataset}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Initiating...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Start Training
                </>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

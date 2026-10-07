import { apiClient } from './client';

export interface MLModelItem {
  id: string;
  name: string;
  algorithm: string;
  version: string;
  dataset_id?: string;
  feature_schema: {
    schema: string;
    features: string[];
  };
  metrics_json: {
    random_split?: {
      r2?: number;
      rmse?: number;
      mae?: number;
      bias?: number;
      nse?: number;
      kge?: number;
    };
    grouped_split?: {
      r2?: number;
      rmse?: number;
      mae?: number;
    };
    conformal?: {
      target_coverage?: number;
      empirical_coverage?: number;
      mean_interval_width?: number;
    };
    cross_validation?: {
      r2?: { mean: number; std: number };
      rmse?: { mean: number; std: number };
    };
    hyperparameters?: Record<string, unknown>;
    shadow_mode?: boolean;
    rejection?: {
      reason: string;
      rejected_by: string;
      rejected_at: string;
    };
    guard_override?: {
      forced_by: string;
      forced_at: string;
    };
    rollback_info?: {
      restored_by: string;
      restored_at: string;
    };
    [key: string]: unknown;
  };
  artifact_uri: string;
  status: 'training' | 'pending_approval' | 'active' | 'archived' | 'rejected';
  trained_by?: string;
  data_provenance: string;
  created_at: string;
  updated_at: string;
}

export interface TrainModelPayload {
  dataset_id: string;
  algorithm?: string;
  algorithms?: string[];
  feature_schema?: string;
  version?: string;
  tune_hyperparameters?: boolean;
  params?: Record<string, unknown>;
}

export interface TrainingJobProgress {
  task_id: string;
  state: 'PENDING' | 'PROGRESS' | 'SUCCESS' | 'FAILURE';
  progress: number;
  current_step: string;
  result?: {
    status: string;
    elapsed_seconds: number;
    trained_models: Array<{
      model_id: string;
      name: string;
      algorithm: string;
      version: string;
    }>;
  };
  error?: string;
}

export interface ShadowReport {
  candidate_model_id: string;
  candidate_version: string;
  candidate_algorithm: string;
  active_model_id?: string;
  active_version?: string;
  sample_count: number;
  mean_difference: number;
  rmse_vs_active: number;
  mae_vs_active: number;
  max_difference: number;
  fao56_correlation?: number;
  recent_samples: Array<{
    id: string;
    prediction_id: string;
    candidate_et_value: number;
    difference_from_active: number;
    latency_ms?: number;
    created_at: string;
  }>;
}

export interface DriftReport {
  drift_detected: boolean;
  drifted_features: string[];
  feature_results: Record<
    string,
    {
      feature: string;
      psi: number;
      psi_drift: boolean;
      psi_severity: string;
      ks_statistic: number;
      ks_pvalue: number;
      ks_drift: boolean;
      is_drifted: boolean;
    }
  >;
  reference_sample_count: number;
  current_sample_count: number;
  psi_threshold: number;
  ks_alpha: number;
  evaluated_at: string;
}

export interface ModelComparisonResponse {
  models: MLModelItem[];
  metrics_matrix: Record<string, Record<string, number>>;
  scatter_samples: Array<{
    index: number;
    y_true: number;
    predictions: Record<string, number>;
  }>;
}

export const listModels = async (status?: string): Promise<MLModelItem[]> => {
  const params = status ? { status } : {};
  const response = await apiClient.get<MLModelItem[]>('/admin/models', { params });
  return response.data;
};

export const getActiveModel = async (): Promise<MLModelItem | null> => {
  const response = await apiClient.get<MLModelItem | null>('/admin/models/active');
  return response.data;
};

export const getModel = async (id: string): Promise<MLModelItem> => {
  const response = await apiClient.get<MLModelItem>(`/admin/models/${id}`);
  return response.data;
};

export const trainModel = async (payload: TrainModelPayload): Promise<{ task_id: string; message: string }> => {
  const response = await apiClient.post<{ task_id: string; message: string }>('/admin/models/train', payload);
  return response.data;
};

export const getJobStatus = async (taskId: string): Promise<TrainingJobProgress> => {
  const response = await apiClient.get<TrainingJobProgress>(`/admin/models/jobs/${taskId}`);
  return response.data;
};

export const approveModel = async (id: string, force = false): Promise<MLModelItem> => {
  const response = await apiClient.post<MLModelItem>(`/admin/models/${id}/approve`, { force });
  return response.data;
};

export const rejectModel = async (id: string, reason: string): Promise<MLModelItem> => {
  const response = await apiClient.post<MLModelItem>(`/admin/models/${id}/reject`, { reason });
  return response.data;
};

export const rollbackModel = async (targetModelId?: string): Promise<MLModelItem> => {
  const response = await apiClient.post<MLModelItem>('/admin/models/rollback', {
    target_model_id: targetModelId,
  });
  return response.data;
};

export const toggleShadowMode = async (id: string, enabled: boolean): Promise<MLModelItem> => {
  const response = await apiClient.post<MLModelItem>(`/admin/models/${id}/shadow`, { enabled });
  return response.data;
};

export const getShadowReport = async (id: string): Promise<ShadowReport> => {
  const response = await apiClient.get<ShadowReport>(`/admin/models/${id}/shadow-report`);
  return response.data;
};

export const compareModels = async (modelIds: string[]): Promise<ModelComparisonResponse> => {
  const response = await apiClient.post<ModelComparisonResponse>('/admin/models/compare', {
    model_ids: modelIds,
  });
  return response.data;
};

export const runDriftCheck = async (params?: {
  window_days?: number;
  psi_threshold?: number;
  ks_alpha?: number;
}): Promise<DriftReport> => {
  const response = await apiClient.post<DriftReport>('/admin/models/drift-check', params || {});
  return response.data;
};

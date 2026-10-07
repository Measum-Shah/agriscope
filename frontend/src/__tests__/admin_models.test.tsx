import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AdminModelsPage } from '../pages/admin/AdminModelsPage';
import { ModelCardModal } from '../components/admin/ModelCardModal';
import * as modelsApi from '../api/models';
import { adminApi } from '../api/admin';

vi.mock('../api/models');
vi.mock('../api/admin');

const mockModels: modelsApi.MLModelItem[] = [
  {
    id: 'm1-active',
    name: 'agriscope_ensemble_basic',
    algorithm: 'ensemble',
    version: 'v1.0',
    status: 'active',
    data_provenance: 'real_derived',
    artifact_uri: 'ml/artifacts/ensemble/v1.0',
    feature_schema: { schema: 'basic', features: ['temp_max', 'temp_min', 'humidity', 'wind_speed'] },
    metrics_json: {
      random_split: { r2: 0.885, rmse: 0.65, mae: 0.45, nse: 0.885, kge: 0.87, bias: -0.02 },
      conformal: { target_coverage: 0.90, empirical_coverage: 0.912, mean_interval_width: 1.15 },
      hyperparameters: { n_estimators: 100 },
    },
    created_at: '2026-10-01T00:00:00Z',
    updated_at: '2026-10-01T00:00:00Z',
  },
  {
    id: 'm2-pending',
    name: 'agriscope_rf_basic',
    algorithm: 'random_forest',
    version: 'v2.0-rf',
    status: 'pending_approval',
    data_provenance: 'real_derived',
    artifact_uri: 'ml/artifacts/rf/v2.0-rf',
    feature_schema: { schema: 'basic', features: ['temp_max', 'temp_min', 'humidity', 'wind_speed'] },
    metrics_json: {
      random_split: { r2: 0.62, rmse: 1.65, mae: 1.20 }, // Fails quality gate (R² < 0.70, RMSE > 1.50)
      shadow_mode: false,
    },
    created_at: '2026-10-02T00:00:00Z',
    updated_at: '2026-10-02T00:00:00Z',
  },
];

describe('AdminModelsPage Frontend', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(modelsApi.listModels).mockResolvedValue(mockModels);
    vi.mocked(adminApi.listDatasets).mockResolvedValue([
      {
        id: 'ds-1',
        name: 'Punjab Weather ET',
        version: 'v1.0',
        file_uri: 's3://datasets/test.csv',
        file_hash: 'hash1',
        status: 'validated',
        data_provenance: 'real_derived',
        stats_json: { row_count: 500 },
        description: null,
        created_at: '2026-10-01T00:00:00Z',
        updated_at: '2026-10-01T00:00:00Z',
      },
    ]);
  });

  it('renders model registry with active and pending models', async () => {
    render(
      <BrowserRouter>
        <AdminModelsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('agriscope_ensemble_basic')).toBeInTheDocument();
      expect(screen.getByText('v1.0')).toBeInTheDocument();
      expect(screen.getByText('agriscope_rf_basic')).toBeInTheDocument();
      expect(screen.getByText('v2.0-rf')).toBeInTheDocument();
    });

    expect(screen.getByText('active')).toBeInTheDocument();
    expect(screen.getByText('pending_approval')).toBeInTheDocument();
  });

  it('ModelCardModal renders metrics and closes', () => {
    const onClose = vi.fn();
    render(
      <ModelCardModal model={mockModels[0]} onClose={onClose} />
    );

    // Modal should be visible with testid
    expect(screen.getByTestId('model-card-modal')).toBeInTheDocument();
    // R² and NSE both equal 0.885 in mock → multiple matches expected
    expect(screen.getAllByText('0.885').length).toBeGreaterThanOrEqual(1);
    // RMSE is unique (0.650)
    expect(screen.getByText('0.650')).toBeInTheDocument();
    // Conformal coverage section
    expect(screen.getByText(/conformal uncertainty calibration/i)).toBeInTheDocument();

    // Close via absolute-positioned X button (first button in modal)
    const closeBtn = screen.getByTestId('model-card-modal').querySelector('button')!;
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalled();
  });


  it('displays quality gate warning on low performing candidate in ApproveModal', async () => {
    render(
      <BrowserRouter>
        <AdminModelsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('agriscope_rf_basic')).toBeInTheDocument();
    });

    const approveButton = screen.getByRole('button', { name: /approve/i });
    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(screen.getByText(/quality gate warning/i)).toBeInTheDocument();
      expect(screen.getByText(/force approval with administrative override/i)).toBeInTheDocument();
    });

    // Toggle force checkbox
    const forceCheckbox = screen.getByRole('checkbox', {
      name: /force approval with administrative override/i,
    });
    fireEvent.click(forceCheckbox);

    vi.mocked(modelsApi.approveModel).mockResolvedValue({
      ...mockModels[1],
      status: 'active',
    });

    const confirmBtn = screen.getByRole('button', { name: /confirm hot swap/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(modelsApi.approveModel).toHaveBeenCalledWith('m2-pending', true);
    });
  });

  it('toggles shadow mode on pending candidate model', async () => {
    render(
      <BrowserRouter>
        <AdminModelsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/disabled/i)).toBeInTheDocument();
    });

    vi.mocked(modelsApi.toggleShadowMode).mockResolvedValue({
      ...mockModels[1],
      metrics_json: { ...mockModels[1].metrics_json, shadow_mode: true },
    });

    const shadowBtn = screen.getByRole('button', { name: /disabled/i });
    fireEvent.click(shadowBtn);

    await waitFor(() => {
      expect(modelsApi.toggleShadowMode).toHaveBeenCalledWith('m2-pending', true);
    });
  });

  it('switches to drift monitoring tab and executes drift check', async () => {
    vi.mocked(modelsApi.runDriftCheck).mockResolvedValue({
      drift_detected: false,
      drifted_features: [],
      feature_results: {
        temperature: {
          feature: 'temperature',
          psi: 0.045,
          psi_drift: false,
          psi_severity: 'none',
          ks_statistic: 0.082,
          ks_pvalue: 0.65,
          ks_drift: false,
          is_drifted: false,
        },
      },
      reference_sample_count: 200,
      current_sample_count: 100,
      psi_threshold: 0.20,
      ks_alpha: 0.05,
      evaluated_at: '2026-10-07T06:00:00Z',
    });

    render(
      <BrowserRouter>
        <AdminModelsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/drift monitoring/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/drift monitoring/i));

    await waitFor(() => {
      expect(screen.getByText(/production data drift monitoring/i)).toBeInTheDocument();
    });

    const runCheckBtn = screen.getByRole('button', { name: /run initial drift analysis/i });
    fireEvent.click(runCheckBtn);

    await waitFor(() => {
      expect(modelsApi.runDriftCheck).toHaveBeenCalled();
      expect(screen.getByText(/distributions stable/i)).toBeInTheDocument();
      expect(screen.getByText('temperature')).toBeInTheDocument();
    });
  });
});

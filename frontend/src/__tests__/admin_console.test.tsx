import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ToastProvider } from '../components/ui/Toast';
import { AdminUsersPage } from '../pages/admin/AdminUsersPage';
import { AdminDatasetsPage } from '../pages/admin/AdminDatasetsPage';
import { AdminOverviewPage } from '../pages/admin/AdminOverviewPage';
import { adminApi } from '../api/admin';

vi.mock('../api/admin', () => ({
  adminApi: {
    getMetrics: vi.fn(),
    listUsers: vi.fn(),
    updateRolePlan: vi.fn(),
    updateStatus: vi.fn(),
    unlockUser: vi.fn(),
    forceLogout: vi.fn(),
    deleteUser: vi.fn(),
    getUserAudit: vi.fn(),
    listDatasets: vi.fn(),
    uploadDataset: vi.fn(),
    deleteDataset: vi.fn(),
    listFeatureFlags: vi.fn(),
    updateFeatureFlag: vi.fn(),
    listAnnouncements: vi.fn(),
    createAnnouncement: vi.fn(),
    toggleAnnouncement: vi.fn(),
    getSystemLimits: vi.fn(),
    updateSystemLimits: vi.fn(),
    listAuditLogs: vi.fn(),
  },
}));

describe('Admin Console Frontend Workflows', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Admin Overview with live KPI stats and active ML model', async () => {
    vi.mocked(adminApi.getMetrics).mockResolvedValue({
      total_users: 154,
      active_users: 142,
      suspended_users: 12,
      predictions_today: 430,
      total_predictions: 12450,
      queue_depth: 0,
      active_model: 'stacking_ensemble_v1',
      error_rate_pct: 0.02,
      latency_p50_ms: 19.5,
      latency_p95_ms: 35.8,
      storage_usage_bytes: 250000000,
      uptime_seconds: 86400,
    });

    render(
      <BrowserRouter>
        <AdminOverviewPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('154')).toBeInTheDocument();
      expect(screen.getByText('430')).toBeInTheDocument();
      expect(screen.getByText('stacking_ensemble_v1')).toBeInTheDocument();
    });
  });

  it('renders Admin Users with actions and triggers confirmation dialog for delete', async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValue({
      items: [
        {
          id: 'user-001',
          name: 'Farmer John',
          email: 'john@farm.io',
          role: 'farmer',
          plan: 'free',
          status: 'active',
          email_verified: true,
          totp_enabled: false,
          failed_attempts: 0,
          locked_until: null,
          registration_date: '2026-10-01T00:00:00Z',
          last_login: null,
        },
      ],
      total: 1,
      page: 1,
      size: 10,
      pages: 1,
    });

    render(
      <BrowserRouter>
        <ToastProvider>
          <AdminUsersPage />
        </ToastProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Farmer John')).toBeInTheDocument();
      expect(screen.getByText('john@farm.io')).toBeInTheDocument();
    });

    // Click delete user button
    const deleteBtn = screen.getByTitle('Delete Account');
    fireEvent.click(deleteBtn);

    // Confirm dialog should open in portal
    await waitFor(() => {
      expect(document.body.textContent).toContain('Permanently Delete User');
      expect(document.body.textContent).toContain('john@farm.io');
    });
  });

  it('renders Datasets page and opens upload modal', async () => {
    vi.mocked(adminApi.listDatasets).mockResolvedValue([
      {
        id: 'ds-100',
        name: 'Punjab Reanalysis',
        version: 'v1.0',
        file_uri: 's3://agriscope-datasets/punjab_v1.csv',
        file_hash: 'sha256abcdef',
        status: 'validated',
        data_provenance: 'user_uploaded',
        stats_json: { row_count: 500 },
        description: 'Station observations',
        created_at: '2026-10-05T00:00:00Z',
        updated_at: '2026-10-05T00:00:00Z',
      },
    ]);

    render(
      <BrowserRouter>
        <ToastProvider>
          <AdminDatasetsPage />
        </ToastProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Punjab Reanalysis')).toBeInTheDocument();
      expect(screen.getByText('v1.0')).toBeInTheDocument();
    });

    // Open upload modal
    const uploadBtn = screen.getByRole('button', { name: /upload new dataset/i });
    fireEvent.click(uploadBtn);

    expect(screen.getByText('Upload Training Dataset')).toBeInTheDocument();
  });
});

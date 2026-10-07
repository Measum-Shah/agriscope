import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ToastProvider } from '../components/ui/Toast';
import { ApiKeysTab } from '../pages/settings/ApiKeysTab';
import { BillingTab } from '../pages/settings/BillingTab';
import { apiKeysApi } from '../api/apiKeys';
import { billingApi } from '../api/billing';

vi.mock('../api/apiKeys', () => ({
  apiKeysApi: {
    list: vi.fn(),
    create: vi.fn(),
    revoke: vi.fn(),
    delete: vi.fn(),
    getUsage: vi.fn(),
  },
}));

vi.mock('../api/billing', () => ({
  billingApi: {
    getSubscription: vi.fn(),
    createCheckoutSession: vi.fn(),
    createPortalSession: vi.fn(),
    mockUpgrade: vi.fn(),
    mockDowngrade: vi.fn(),
  },
}));

const mockAuthContext = {
  user: {
    id: 'user-pro-1',
    name: 'Researcher Alice',
    email: 'alice@lab.org',
    role: 'researcher' as const,
    plan: 'pro' as const,
    status: 'active' as const,
    email_verified: true,
    totp_enabled: false,
  },
  entitlements: {
    plan: 'pro' as const,
    daily_prediction_limit: null,
    predictions_used_today: 5,
    predictions_remaining_today: null,
    features: {
      manual_et: true,
      location_weather: true,
      single_field: true,
      basic_crops: true,
      export_csv: true,
      satellite_indices: true,
      sentinel_pipeline: true,
      custom_kc: true,
      advanced_crops: true,
      export_geojson: true,
      pdf_report: true,
      api_access: true,
      unlimited_fields: true,
      priority_inference: true,
    },
  },
  refreshUser: vi.fn(),
};

vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockAuthContext,
}));

describe('API Keys & Billing Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders API Keys list and creates a new key with secret prompt', async () => {
    vi.mocked(apiKeysApi.list).mockResolvedValue([
      {
        id: 'key-1',
        name: 'Field Sensor Ingest',
        key_prefix: 'agri_live_7a8b',
        scopes: ['predict:read'],
        rate_limit_per_min: 60,
        daily_limit: 5000,
        created_at: '2026-10-07T05:00:00Z',
        last_used_at: null,
        expires_at: null,
        is_active: true,
      },
    ]);

    vi.mocked(apiKeysApi.create).mockResolvedValue({
      id: 'key-2',
      name: 'Batch Pipeline',
      raw_key: 'agri_live_secret1234567890',
      key_prefix: 'agri_live_secr',
      scopes: ['predict:read', 'batch:write'],
      rate_limit_per_min: 60,
      daily_limit: 5000,
      created_at: '2026-10-07T05:10:00Z',
      expires_at: null,
      warning: 'Store this key now. It will not be shown again.',
    });

    render(
      <BrowserRouter>
        <ToastProvider>
          <ApiKeysTab />
        </ToastProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Field Sensor Ingest')).toBeInTheDocument();
      expect(screen.getByText('predict:read')).toBeInTheDocument();
    });

    // Open creation modal
    fireEvent.click(screen.getByRole('button', { name: /generate new key/i }));
    expect(screen.getByText('Create Researcher API Key')).toBeInTheDocument();

    const nameInput = screen.getByPlaceholderText(/Drone Telemetry Ingestion/i);
    fireEvent.change(nameInput, { target: { value: 'Batch Pipeline' } });

    // Submit form
    fireEvent.click(screen.getByRole('button', { name: /^generate key$/i }));

    await waitFor(() => {
      expect(apiKeysApi.create).toHaveBeenCalledWith({
        name: 'Batch Pipeline',
        scopes: ['predict:read'],
      });
      expect(screen.getByText('agri_live_secret1234567890')).toBeInTheDocument();
    });
  });

  it('renders Billing subscription plan and triggers mock downgrade/upgrade', async () => {
    vi.mocked(billingApi.getSubscription).mockResolvedValue({
      plan: 'pro',
      status: 'active',
      stripe_customer_id: 'cus_123',
      stripe_subscription_id: 'sub_123',
      current_period_end: '2026-11-07T00:00:00Z',
      cancel_at_period_end: false,
    });

    vi.mocked(billingApi.createPortalSession).mockRejectedValue(new Error('Stripe not configured'));
    vi.mocked(billingApi.mockDowngrade).mockResolvedValue({
      success: true,
      message: 'Plan downgraded to free',
      plan: 'free',
    });

    render(
      <BrowserRouter>
        <ToastProvider>
          <BillingTab />
        </ToastProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/AgriScope pro Tier/i)).toBeInTheDocument();
      expect(screen.getByText(/Pro Researcher/i)).toBeInTheDocument();
    });

    const downgradeBtn = screen.getByRole('button', { name: /switch to free/i });
    fireEvent.click(downgradeBtn);

    await waitFor(() => {
      expect(billingApi.mockDowngrade).toHaveBeenCalled();
    });
  });
});

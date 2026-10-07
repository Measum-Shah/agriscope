import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PredictPage } from '../pages/predict/PredictPage';
import { HistoryPage } from '../pages/history/HistoryPage';
import * as AuthContextModule from '../context/AuthContext';
import { ToastProvider } from '../components/ui/Toast';

vi.mock('../api/predict', () => ({
  predictApi: {
    predict: vi.fn(),
    compare: vi.fn(),
    explain: vi.fn(),
    getSample: vi.fn().mockResolvedValue({
      temperature: 28.0,
      humidity: 50.0,
      wind_speed: 2.2,
      solar_radiation: 22.0,
      tmin: 22.0,
      tmax: 34.0,
      latitude: 31.5,
      elevation: 100,
      doy: 180,
      location_name: 'Multan, Pakistan',
      description: 'Peak arid summer wheat-cotton rotation',
    }),
  },
}));

vi.mock('../api/history', () => ({
  historyApi: {
    list: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'test-pred-1',
          et_value: 4.85,
          interval_low: 4.35,
          interval_high: 5.35,
          confidence_level: 0.9,
          classification: 'moderate',
          model_version: 'v1.0',
          model_algorithm: 'stacking_ensemble',
          created_at: '2026-10-07T00:00:00Z',
          is_saved: false,
          tags: ['wheat'],
          note: 'Pivot A trial',
        },
      ],
      total: 1,
      page: 1,
      per_page: 15,
      total_pages: 1,
    }),
    getStats: vi.fn().mockResolvedValue({
      total_predictions: 1,
      today_predictions: 1,
      quota_remaining_today: 29,
      quota_limit_today: 30,
      mean_et: 4.85,
      latest_et: 4.85,
      classification_counts: { moderate: 1 },
      trend_7d: [{ date: '2026-10-07', mean_et: 4.85, count: 1 }],
    }),
    update: vi.fn(),
    delete: vi.fn(),
    bulkDelete: vi.fn(),
  },
}));

const mockAuthValue = {
  user: {
    id: '123',
    name: 'Farmer Joe',
    email: 'farmer@agriscope.local',
    role: 'free',
    plan: 'free',
    status: 'active',
    email_verified: true,
    totp_enabled: false,
  },
  entitlements: {
    plan: 'free',
    daily_prediction_limit: 30,
    predictions_used_today: 1,
    predictions_remaining_today: 29,
    features: {},
  },
  isLoading: false,
  isAuthenticated: true,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  refreshUser: vi.fn(),
  refreshEntitlements: vi.fn(),
};

const renderWithProviders = (ui: React.ReactElement) => {
  vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue(
    mockAuthValue as unknown as AuthContextModule.AuthContextType
  );
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>{ui}</BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  );
};

describe('PredictPage and HistoryPage', () => {
  it('renders PredictPage with meteorological parameters form', () => {
    renderWithProviders(<PredictPage />);
    expect(screen.getByText(/Evapotranspiration Estimation/i)).toBeInTheDocument();
    expect(screen.getByText(/Temperature \(°C\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Relative Humidity \(%\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Calculate Evapotranspiration/i)).toBeInTheDocument();
  });

  it('renders HistoryPage with table and 7-day trend section', async () => {
    renderWithProviders(<HistoryPage />);
    expect(screen.getByText(/Prediction History & Trends/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getAllByText(/4.85/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/Pivot A trial/i)).toBeInTheDocument();
    });
  });
});

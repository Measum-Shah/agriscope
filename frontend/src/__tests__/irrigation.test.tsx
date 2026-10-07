import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastProvider } from '../components/ui/Toast';
import { IrrigationPage } from '../pages/irrigation/IrrigationPage';
import * as AuthContextModule from '../context/AuthContext';

vi.mock('../api/fields', () => ({
  fieldsApi: {
    getFields: vi.fn().mockResolvedValue([
      {
        id: 'field-101',
        name: 'Sector 7 Cotton Block',
        crop_id: 'crop-101',
        crop_name: 'Cotton',
        planting_date: '2026-05-01',
        area_ha: 12.0,
        geometry: { type: 'Polygon', coordinates: [] },
        created_at: '2026-05-01T00:00:00Z',
        updated_at: '2026-05-01T00:00:00Z',
      },
    ]),
  },
}));

vi.mock('../api/irrigation', () => ({
  irrigationApi: {
    getPlan: vi.fn().mockResolvedValue({
      field_id: 'field-101',
      field_name: 'Sector 7 Cotton Block',
      crop_name: 'Cotton',
      area_ha: 12.0,
      soil_type: 'Loam',
      planting_date: '2026-05-01',
      mad_fraction: 0.5,
      summary: {
        total_etc_mm: 145.2,
        total_rainfall_mm: 35.0,
        total_effective_rain_mm: 23.0,
        total_irrigation_applied_mm: 50.0,
        net_irrigation_requirement_mm: 122.2,
        current_depletion_mm: 42.5,
        raw_mm: 55.0,
        taw_mm: 110.0,
        status: 'caution',
      },
      schedule: [
        {
          date: '2026-10-07',
          day_name: 'Wed',
          depletion_mm: 42.5,
          raw_threshold_mm: 55.0,
          is_irrigation_due: false,
          recommended_depth_mm: 0.0,
          recommended_volume_m3_per_ha: 0.0,
          recommended_volume_m3_total: 0.0,
          reason: 'Optimal soil moisture',
        },
        {
          date: '2026-10-08',
          day_name: 'Thu',
          depletion_mm: 56.2,
          raw_threshold_mm: 55.0,
          is_irrigation_due: true,
          recommended_depth_mm: 56.2,
          recommended_volume_m3_per_ha: 562.0,
          recommended_volume_m3_total: 6744.0,
          reason: 'Soil moisture depleted below RAW threshold',
        },
      ],
      daily_balance: [
        {
          date: '2026-10-07',
          et0_mm: 4.8,
          kc: 1.15,
          etc_mm: 5.52,
          rain_mm: 0.0,
          effective_rain_mm: 0.0,
          irrigation_applied_mm: 0.0,
          root_depth_m: 0.8,
          taw_mm: 110.0,
          raw_mm: 55.0,
          depletion_mm: 42.5,
          is_stress: false,
          irrigation_recommended_mm: 0.0,
        },
      ],
      events: [
        {
          id: 'ev-1',
          field_id: 'field-101',
          event_date: '2026-10-01',
          water_applied_mm: 25.0,
          method: 'drip',
          notes: 'Regular cycle',
        },
      ],
    }),
    logEvent: vi.fn().mockResolvedValue({
      id: 'ev-2',
      field_id: 'field-101',
      event_date: '2026-10-07',
      water_applied_mm: 30.0,
      method: 'drip',
      notes: 'New cycle',
    }),
    deleteEvent: vi.fn().mockResolvedValue({ ok: true, message: 'Deleted' }),
  },
}));

const renderWithProviders = (ui: React.ReactElement) => {
  vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
    user: {
      id: 'user-1',
      email: 'irrigator@agriscope.local',
      name: 'Lead Agronomist',
      role: 'agronomist',
      plan: 'pro',
      status: 'active',
      email_verified: true,
      totp_enabled: false,
    },
    entitlements: null,
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
    refreshEntitlements: vi.fn(),
  });

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

describe('IrrigationPage & Soil Water Balance', () => {
  it('renders IrrigationPage with summary cards and schedule table', async () => {
    renderWithProviders(<IrrigationPage />);

    expect(
      screen.getByText(/Crop Water Requirement & Irrigation Scheduling/i)
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Log Applied Irrigation/i })).toBeInTheDocument();

    // Verify Summary KPI rendering
    expect(await screen.findByText(/Net Irrigation Req \(NIR\)/i)).toBeInTheDocument();
    expect(screen.getByText(/122.2 mm/i)).toBeInTheDocument();
    expect(screen.getByText(/7-Day Irrigation Schedule/i)).toBeInTheDocument();
    expect(screen.getByText(/Applied Water Events/i)).toBeInTheDocument();
  });
});

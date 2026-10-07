import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastProvider } from '../components/ui/Toast';
import { FieldsPage } from '../pages/fields/FieldsPage';
import { RemoteSensingPage } from '../pages/remote-sensing/RemoteSensingPage';

// Mock API modules
vi.mock('../api/fields', () => ({
  fieldsApi: {
    getFields: vi.fn().mockResolvedValue([
      {
        id: 'field-1',
        name: 'Punjab Wheat Sector A',
        crop_id: 'crop-1',
        crop_name: 'Wheat',
        planting_date: '2026-11-01',
        area_ha: 4.5,
        geometry: {
          type: 'Polygon',
          coordinates: [
            [
              [74.3, 31.5],
              [74.31, 31.5],
              [74.31, 31.51],
              [74.3, 31.51],
              [74.3, 31.5],
            ],
          ],
        },
        created_at: '2026-10-01T00:00:00Z',
        updated_at: '2026-10-01T00:00:00Z',
      },
    ]),
    getCrops: vi.fn().mockResolvedValue([
      { id: 'crop-1', name: 'Wheat', kc_ini: 0.3, kc_mid: 1.15, kc_end: 0.4 },
    ]),
    createField: vi.fn(),
    deleteField: vi.fn(),
  },
}));

vi.mock('../api/remoteSensing', () => ({
  remoteSensingApi: {
    getObservations: vi.fn().mockResolvedValue([
      {
        id: 'obs-1',
        field_id: 'field-1',
        observation_date: '2026-10-05',
        ndvi: 0.65,
        evi: 0.52,
        ndwi: 0.18,
        cloud_cover_pct: 5.2,
        et0: 4.5,
        kc: 0.95,
        etc: 4.28,
        rain_mm: 0.0,
      },
    ]),
    analyzeField: vi.fn(),
  },
}));

import * as AuthContextModule from '../context/AuthContext';

// Mock Leaflet
vi.mock('leaflet', () => {
  const mapMock = {
    setView: vi.fn().mockReturnThis(),
    on: vi.fn(),
    remove: vi.fn(),
  };
  return {
    default: {
      map: vi.fn(() => mapMock),
      tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
      polygon: vi.fn(() => ({ addTo: vi.fn(), remove: vi.fn() })),
      circleMarker: vi.fn(() => ({ bindTooltip: vi.fn().mockReturnThis(), addTo: vi.fn() })),
      layerGroup: vi.fn(() => ({ addTo: vi.fn(), clearLayers: vi.fn() })),
      Icon: {
        Default: {
          prototype: {},
          mergeOptions: vi.fn(),
        },
      },
    },
  };
});

const renderWithProviders = (ui: React.ReactElement) => {
  vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
    user: {
      id: 'user-1',
      email: 'farmer@agriscope.local',
      name: 'Farmer John',
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

describe('Fields & Remote Sensing Frontend Pages', () => {
  it('renders FieldsPage with parcel list and add field button', async () => {
    renderWithProviders(<FieldsPage />);

    expect(screen.getByText(/Fields & Parcels/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Add Field/i })).toBeInTheDocument();
    expect(await screen.findByText(/Punjab Wheat Sector A/i)).toBeInTheDocument();
  });

  it('renders RemoteSensingPage with satellite indices analytics and controls', async () => {
    renderWithProviders(<RemoteSensingPage />);

    expect(
      screen.getByText(/Remote Sensing & Satellite Analytics/i)
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Refresh Analysis/i })).toBeInTheDocument();
    expect(await screen.findByText(/Canopy Vegetation Indices/i)).toBeInTheDocument();
    expect(screen.getByText(/Satellite Scenes Log/i)).toBeInTheDocument();
  });
});

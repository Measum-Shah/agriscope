import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '../routes/ProtectedRoute';
import { RoleRoute } from '../routes/RoleRoute';
import { PlanRoute } from '../routes/PlanRoute';
import * as AuthContextModule from '../context/AuthContext';
import { User, Entitlements } from '../types/auth';

const mockFreeUser: User = {
  id: 'usr-1',
  name: 'Test Farmer',
  email: 'farmer@test.org',
  role: 'farmer',
  plan: 'free',
  status: 'active',
  email_verified: true,
  totp_enabled: false,
};

const mockAdminUser: User = {
  id: 'usr-2',
  name: 'Admin User',
  email: 'admin@agriscope.io',
  role: 'admin',
  plan: 'admin',
  status: 'active',
  email_verified: true,
  totp_enabled: true,
};

const mockFreeEntitlements: Entitlements = {
  plan: 'free',
  daily_prediction_limit: 10,
  predictions_used_today: 0,
  predictions_remaining_today: 10,
  features: {
    manual_et: true,
    location_weather: true,
    single_field: true,
    basic_crops: true,
    export_csv: true,
    satellite_indices: false,
    sentinel_pipeline: false,
    custom_kc: false,
    advanced_crops: false,
    export_geojson: false,
    pdf_report: false,
    api_access: false,
    unlimited_fields: false,
    priority_inference: false,
  },
};

describe('Route Guards', () => {
  describe('ProtectedRoute', () => {
    it('redirects to /login when unauthenticated', () => {
      vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
        user: null,
        entitlements: null,
        isLoading: false,
        isAuthenticated: false,
        login: vi.fn(),
        register: vi.fn(),
        logout: vi.fn(),
        refreshUser: vi.fn(),
        refreshEntitlements: vi.fn(),
      });

      render(
        <MemoryRouter initialEntries={['/dashboard']}>
          <Routes>
            <Route path="/login" element={<div>Login Page Mock</div>} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <div>Secret Dashboard</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('Login Page Mock')).toBeInTheDocument();
      expect(screen.queryByText('Secret Dashboard')).not.toBeInTheDocument();
    });

    it('renders protected child when authenticated', () => {
      vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
        user: mockFreeUser,
        entitlements: mockFreeEntitlements,
        isLoading: false,
        isAuthenticated: true,
        login: vi.fn(),
        register: vi.fn(),
        logout: vi.fn(),
        refreshUser: vi.fn(),
        refreshEntitlements: vi.fn(),
      });

      render(
        <MemoryRouter initialEntries={['/dashboard']}>
          <Routes>
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <div>Secret Dashboard Content</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('Secret Dashboard Content')).toBeInTheDocument();
    });
  });

  describe('RoleRoute', () => {
    it('shows Access Restricted card when user lacks allowed role', () => {
      vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
        user: mockFreeUser, // role: farmer
        entitlements: mockFreeEntitlements,
        isLoading: false,
        isAuthenticated: true,
        login: vi.fn(),
        register: vi.fn(),
        logout: vi.fn(),
        refreshUser: vi.fn(),
        refreshEntitlements: vi.fn(),
      });

      render(
        <MemoryRouter initialEntries={['/admin']}>
          <Routes>
            <Route
              path="/admin"
              element={
                <RoleRoute allowedRoles={['admin']}>
                  <div>Admin Secret Area</div>
                </RoleRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('Access Restricted')).toBeInTheDocument();
      expect(screen.queryByText('Admin Secret Area')).not.toBeInTheDocument();
    });

    it('grants access when role is in allowed list', () => {
      vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
        user: mockAdminUser,
        entitlements: mockFreeEntitlements,
        isLoading: false,
        isAuthenticated: true,
        login: vi.fn(),
        register: vi.fn(),
        logout: vi.fn(),
        refreshUser: vi.fn(),
        refreshEntitlements: vi.fn(),
      });

      render(
        <MemoryRouter initialEntries={['/admin']}>
          <Routes>
            <Route
              path="/admin"
              element={
                <RoleRoute allowedRoles={['admin']}>
                  <div>Admin Secret Area</div>
                </RoleRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('Admin Secret Area')).toBeInTheDocument();
    });
  });

  describe('PlanRoute', () => {
    it('shows upgrade prompt when feature is not entitled', () => {
      vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
        user: mockFreeUser,
        entitlements: mockFreeEntitlements, // satellite_indices: false
        isLoading: false,
        isAuthenticated: true,
        login: vi.fn(),
        register: vi.fn(),
        logout: vi.fn(),
        refreshUser: vi.fn(),
        refreshEntitlements: vi.fn(),
      });

      render(
        <MemoryRouter initialEntries={['/remote-sensing']}>
          <Routes>
            <Route
              path="/remote-sensing"
              element={
                <PlanRoute requiredFeature="satellite_indices">
                  <div>Satellite Analytics View</div>
                </PlanRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('Pro Feature')).toBeInTheDocument();
      expect(screen.queryByText('Satellite Analytics View')).not.toBeInTheDocument();
    });

    it('allows access when user has admin role or entitlement', () => {
      vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
        user: mockAdminUser,
        entitlements: mockFreeEntitlements,
        isLoading: false,
        isAuthenticated: true,
        login: vi.fn(),
        register: vi.fn(),
        logout: vi.fn(),
        refreshUser: vi.fn(),
        refreshEntitlements: vi.fn(),
      });

      render(
        <MemoryRouter initialEntries={['/remote-sensing']}>
          <Routes>
            <Route
              path="/remote-sensing"
              element={
                <PlanRoute requiredFeature="satellite_indices">
                  <div>Satellite Analytics View</div>
                </PlanRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('Satellite Analytics View')).toBeInTheDocument();
    });
  });
});

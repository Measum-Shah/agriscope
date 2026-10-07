import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import axe from 'axe-core';
import { LoginPage } from '../pages/auth/Login';
import { RegisterPage } from '../pages/auth/Register';
import { ForgotPasswordPage } from '../pages/auth/ForgotPassword';
import { ResetPasswordPage } from '../pages/auth/ResetPassword';
import { VerifyEmailPage } from '../pages/auth/VerifyEmail';
import { ToastProvider } from '../components/ui/Toast';
import * as AuthContextModule from '../context/AuthContext';

describe('Axe Accessibility Checks on Auth Pages', () => {
  const setupAuthMock = () => {
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
  };

  const runAxe = async (container: HTMLElement) => {
    return await axe.run(container, {
      rules: {
        // jsdom does not compute layout bounding boxes for color-contrast
        'color-contrast': { enabled: false },
      },
    });
  };

  it('LoginPage passes axe accessibility audit', async () => {
    setupAuthMock();
    const { container } = render(
      <ToastProvider>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </ToastProvider>
    );

    const results = await runAxe(container);
    expect(results.violations).toEqual([]);
  });

  it('RegisterPage passes axe accessibility audit', async () => {
    setupAuthMock();
    const { container } = render(
      <ToastProvider>
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      </ToastProvider>
    );

    const results = await runAxe(container);
    expect(results.violations).toEqual([]);
  });

  it('ForgotPasswordPage passes axe accessibility audit', async () => {
    setupAuthMock();
    const { container } = render(
      <ToastProvider>
        <MemoryRouter>
          <ForgotPasswordPage />
        </MemoryRouter>
      </ToastProvider>
    );

    const results = await runAxe(container);
    expect(results.violations).toEqual([]);
  });

  it('ResetPasswordPage passes axe accessibility audit', async () => {
    setupAuthMock();
    const { container } = render(
      <ToastProvider>
        <MemoryRouter>
          <ResetPasswordPage />
        </MemoryRouter>
      </ToastProvider>
    );

    const results = await runAxe(container);
    expect(results.violations).toEqual([]);
  });

  it('VerifyEmailPage passes axe accessibility audit', async () => {
    setupAuthMock();
    const { container } = render(
      <ToastProvider>
        <MemoryRouter>
          <VerifyEmailPage />
        </MemoryRouter>
      </ToastProvider>
    );

    const results = await runAxe(container);
    expect(results.violations).toEqual([]);
  });

  it('DashboardPage passes axe accessibility audit', async () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: {
        id: 'u-1',
        name: 'Test Farmer',
        email: 'farmer@agriscope.dev',
        role: 'farmer',
        plan: 'pro',
        status: 'active',
        email_verified: true,
        totp_enabled: false,
      },
      entitlements: {
        plan: 'pro',
        daily_prediction_limit: 1000,
        predictions_used_today: 5,
        predictions_remaining_today: 995,
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
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
      refreshEntitlements: vi.fn(),
    });

    const { DashboardPage } = await import('../pages/dashboard/DashboardPage');
    const { container } = render(
      <ToastProvider>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </ToastProvider>
    );

    const results = await runAxe(container);
    expect(results.violations).toEqual([]);
  });
});

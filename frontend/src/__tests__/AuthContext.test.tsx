import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { authApi } from '../api/auth';
import { usersApi } from '../api/users';
import { User, Entitlements } from '../types/auth';

const mockUser: User = {
  id: 'u-123',
  name: 'Amina Agronomist',
  email: 'amina@farm.pk',
  role: 'agronomist',
  plan: 'free',
  status: 'active',
  email_verified: true,
  totp_enabled: false,
};

const mockEntitlements: Entitlements = {
  plan: 'free',
  daily_prediction_limit: 10,
  predictions_used_today: 2,
  predictions_remaining_today: 8,
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

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('hydrates user on mount if refresh token is present', async () => {
    vi.spyOn(authApi, 'refresh').mockResolvedValue({
      access_token: 'fresh-access-token',
      token_type: 'bearer',
    });
    vi.spyOn(usersApi, 'getProfile').mockResolvedValue(mockUser);
    vi.spyOn(usersApi, 'getEntitlements').mockResolvedValue(mockEntitlements);

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthProvider>{children}</AuthProvider>
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {});

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.name).toBe('Amina Agronomist');
    expect(result.current.entitlements?.predictions_used_today).toBe(2);
  });

  it('handles login with 2FA required challenge', async () => {
    vi.spyOn(authApi, 'refresh').mockRejectedValue(new Error('No token'));
    vi.spyOn(authApi, 'login').mockRejectedValue({
      response: {
        data: {
          code: '2FA_REQUIRED',
          detail: '2FA_REQUIRED:temp-token',
        },
      },
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthProvider>{children}</AuthProvider>
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {});

    let loginResult;
    await act(async () => {
      loginResult = await result.current.login({
        email: 'user@farm.org',
        password: 'Password123!',
      });
    });

    expect(loginResult).toEqual({ requires2FA: true });
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('handles logout and clears state', async () => {
    vi.spyOn(authApi, 'refresh').mockResolvedValue({
      access_token: 'fresh-access-token',
      token_type: 'bearer',
    });
    vi.spyOn(usersApi, 'getProfile').mockResolvedValue(mockUser);
    vi.spyOn(usersApi, 'getEntitlements').mockResolvedValue(mockEntitlements);
    vi.spyOn(authApi, 'logout').mockResolvedValue();

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthProvider>{children}</AuthProvider>
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {});
    expect(result.current.isAuthenticated).toBe(true);

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.entitlements).toBeNull();
  });
});

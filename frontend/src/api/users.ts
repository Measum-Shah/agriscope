import { apiClient } from './client';
import {
  AuditLogItem,
  Entitlements,
  TOTPSetupResponse,
  TOTPVerifyResponse,
  User,
} from '../types/auth';

export interface UpdateProfilePayload {
  name?: string;
}

export interface ChangeEmailPayload {
  new_email: string;
  password: string;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export interface Disable2FAPayload {
  password: string;
  code?: string;
}

export const usersApi = {
  async getEntitlements(): Promise<Entitlements> {
    const res = await apiClient.get<Entitlements>('/users/me/entitlements');
    return res.data;
  },

  async getProfile(): Promise<User> {
    const res = await apiClient.get<User>('/users/me');
    return res.data;
  },

  async updateProfile(payload: UpdateProfilePayload): Promise<User> {
    const res = await apiClient.patch<User>('/users/me/profile', payload);
    return res.data;
  },

  async changeEmail(payload: ChangeEmailPayload): Promise<{ message: string }> {
    const res = await apiClient.post<{ message: string }>('/users/me/change-email', payload);
    return res.data;
  },

  async confirmEmailChange(token: string): Promise<{ message: string }> {
    const res = await apiClient.post<{ message: string }>('/users/me/confirm-email-change', {
      token,
    });
    return res.data;
  },

  async changePassword(payload: ChangePasswordPayload): Promise<{ message: string }> {
    const res = await apiClient.post<{ message: string }>('/users/me/change-password', payload);
    return res.data;
  },

  async setup2FA(): Promise<TOTPSetupResponse> {
    const res = await apiClient.post<TOTPSetupResponse>('/users/me/2fa/setup');
    return res.data;
  },

  async verify2FA(code: string): Promise<TOTPVerifyResponse> {
    const res = await apiClient.post<TOTPVerifyResponse>('/users/me/2fa/verify', {
      code,
    });
    return res.data;
  },

  async disable2FA(payload: Disable2FAPayload): Promise<{ message: string }> {
    const res = await apiClient.post<{ message: string }>('/users/me/2fa/disable', payload);
    return res.data;
  },

  async exportData(): Promise<Record<string, unknown>> {
    const res = await apiClient.get<Record<string, unknown>>('/users/me/export');
    return res.data;
  },

  async deleteAccount(password: string): Promise<{ message: string }> {
    const res = await apiClient.delete<{ message: string }>('/users/me', {
      data: { password },
    });
    return res.data;
  },

  async getAuditLogs(): Promise<AuditLogItem[]> {
    const res = await apiClient.get<AuditLogItem[]>('/users/me/audit');
    return res.data;
  },
};

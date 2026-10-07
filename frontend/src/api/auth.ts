import { apiClient } from './client';
import { AuthTokens, LoginResponse, SessionInfo, User } from '../types/auth';

export interface RegisterPayload {
  email: string;
  password: string;
  name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
  totp_code?: string;
  recovery_code?: string;
}

export interface ResetPasswordPayload {
  token: string;
  new_password: string;
}

export const authApi = {
  async register(payload: RegisterPayload): Promise<User> {
    const res = await apiClient.post<User>('/auth/register', payload);
    return res.data;
  },

  async login(payload: LoginPayload): Promise<LoginResponse> {
    const res = await apiClient.post<LoginResponse>('/auth/login', payload);
    return res.data;
  },

  async refresh(): Promise<AuthTokens> {
    const res = await apiClient.post<AuthTokens>('/auth/refresh');
    return res.data;
  },

  async logout(): Promise<void> {
    await apiClient.post('/auth/logout');
  },

  async logoutAll(): Promise<void> {
    await apiClient.post('/auth/logout-all');
  },

  async getMe(): Promise<User> {
    const res = await apiClient.get<User>('/auth/me');
    return res.data;
  },

  async getSessions(): Promise<SessionInfo[]> {
    const res = await apiClient.get<SessionInfo[]>('/auth/sessions');
    return res.data;
  },

  async revokeSession(sessionId: string): Promise<void> {
    await apiClient.delete(`/auth/sessions/${sessionId}`);
  },

  async verifyEmail(token: string): Promise<{ message: string }> {
    const res = await apiClient.post<{ message: string }>('/auth/verify-email', {
      token,
    });
    return res.data;
  },

  async resendVerification(email: string): Promise<{ message: string }> {
    const res = await apiClient.post<{ message: string }>('/auth/resend-verification', { email });
    return res.data;
  },

  async forgotPassword(email: string): Promise<{ message: string }> {
    const res = await apiClient.post<{ message: string }>('/auth/forgot-password', { email });
    return res.data;
  },

  async resetPassword(payload: ResetPasswordPayload): Promise<{ message: string }> {
    const res = await apiClient.post<{ message: string }>('/auth/reset-password', payload);
    return res.data;
  },
};

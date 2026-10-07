import { apiClient } from './client';

export interface SubscriptionInfo {
  plan: string;
  status: string;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

export interface CheckoutSessionResponse {
  checkout_url: string;
  session_id: string;
}

export interface PortalSessionResponse {
  portal_url: string;
}

export const billingApi = {
  getSubscription: async (): Promise<SubscriptionInfo> => {
    const res = await apiClient.get<SubscriptionInfo>('/billing/subscription');
    return res.data;
  },

  createCheckoutSession: async (plan: 'pro' = 'pro'): Promise<CheckoutSessionResponse> => {
    const res = await apiClient.post<CheckoutSessionResponse>('/billing/checkout', { plan });
    return res.data;
  },

  createPortalSession: async (): Promise<PortalSessionResponse> => {
    const res = await apiClient.post<PortalSessionResponse>('/billing/portal');
    return res.data;
  },

  mockUpgrade: async (plan: string = 'pro'): Promise<{ success: boolean; message: string; plan: string }> => {
    const res = await apiClient.post<{ success: boolean; message: string; plan: string }>('/billing/mock/upgrade', {
      plan,
    });
    return res.data;
  },

  mockDowngrade: async (): Promise<{ success: boolean; message: string; plan: string }> => {
    const res = await apiClient.post<{ success: boolean; message: string; plan: string }>('/billing/mock/downgrade');
    return res.data;
  },
};

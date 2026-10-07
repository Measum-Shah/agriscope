import React, { createContext, useContext, useEffect, useState } from 'react';
import { authApi, LoginPayload, RegisterPayload } from '../api/auth';
import { usersApi } from '../api/users';
import { clearAccessToken, setAccessToken } from '../api/client';
import { Entitlements, User } from '../types/auth';

export interface AuthContextType {
  user: User | null;
  entitlements: Entitlements | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginPayload) => Promise<{ requires2FA?: boolean }>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  refreshEntitlements: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [entitlements, setEntitlements] = useState<Entitlements | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshEntitlements = async () => {
    try {
      const ent = await usersApi.getEntitlements();
      setEntitlements(ent);
    } catch {
      // Ignore or let fallback
    }
  };

  const refreshUser = async () => {
    try {
      const profile = await usersApi.getProfile();
      setUser(profile);
      await refreshEntitlements();
    } catch {
      setUser(null);
      setEntitlements(null);
    }
  };

  // Initial silent token refresh on app launch
  useEffect(() => {
    let isMounted = true;

    const bootstrapAuth = async () => {
      try {
        const tokens = await authApi.refresh();
        if (tokens?.access_token) {
          setAccessToken(tokens.access_token);
          const profile = await usersApi.getProfile();
          if (isMounted) {
            setUser(profile);
            const ent = await usersApi.getEntitlements();
            setEntitlements(ent);
          }
        }
      } catch {
        if (isMounted) {
          setUser(null);
          setEntitlements(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    bootstrapAuth();

    const handleUnauthorized = () => {
      setUser(null);
      setEntitlements(null);
      clearAccessToken();
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);

    return () => {
      isMounted = false;
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, []);

  const login = async (credentials: LoginPayload) => {
    try {
      const response = await authApi.login(credentials);
      if (response.access_token) {
        setAccessToken(response.access_token);
        if (response.user) {
          setUser(response.user);
        } else {
          const profile = await usersApi.getProfile();
          setUser(profile);
        }
        await refreshEntitlements();
        return { requires2FA: false };
      }
      return { requires2FA: false };
    } catch (err: unknown) {
      const errorObj = err as {
        response?: { data?: { detail?: string; code?: string } };
      };
      if (
        errorObj.response?.data?.code === '2FA_REQUIRED' ||
        errorObj.response?.data?.detail?.startsWith('2FA_REQUIRED:')
      ) {
        return { requires2FA: true };
      }
      throw err;
    }
  };

  const register = async (payload: RegisterPayload) => {
    return await authApi.register(payload);
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } finally {
      clearAccessToken();
      setUser(null);
      setEntitlements(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        entitlements,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshUser,
        refreshEntitlements,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

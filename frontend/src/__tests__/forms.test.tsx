import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LoginPage } from '../pages/auth/Login';
import { RegisterPage } from '../pages/auth/Register';
import { ToastProvider } from '../components/ui/Toast';
import * as AuthContextModule from '../context/AuthContext';

describe('Authentication Form Components', () => {
  it('renders login page with form inputs and displays validation errors for invalid submission', async () => {
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
      <ToastProvider>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </ToastProvider>
    );

    expect(screen.getByLabelText(/Email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /Sign In/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Please enter a valid email address/i)).toBeInTheDocument();
    });
  });

  it('renders register form and flags password confirmation mismatches', async () => {
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
      <ToastProvider>
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      </ToastProvider>
    );

    fireEvent.change(screen.getByLabelText(/Full Name/i), {
      target: { value: 'Dr. Tariq' },
    });
    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: 'tariq@agri.org' },
    });
    fireEvent.change(screen.getByLabelText(/^Password/i), {
      target: { value: 'ValidPass1' },
    });
    fireEvent.change(screen.getByLabelText(/Confirm Password/i), {
      target: { value: 'MismatchPass2' },
    });

    fireEvent.click(screen.getByRole('button', { name: /Create Account/i }));

    await waitFor(() => {
      expect(screen.getByText(/Passwords do not match/i)).toBeInTheDocument();
    });
  });
});

import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from '../App';
import * as authApiModule from '../api/auth';

describe('AgriScope Application Root', () => {
  it('renders application and navigates to login when unauthenticated', async () => {
    vi.spyOn(authApiModule.authApi, 'refresh').mockRejectedValue(new Error('Unauthenticated'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Sign in to AgriScope/i })).toBeInTheDocument();
    });

    expect(screen.getByLabelText(/Email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Password/i)).toBeInTheDocument();
  });
});

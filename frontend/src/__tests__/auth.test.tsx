import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import LoginPage from '@/app/(auth)/login/page';
import { AuthProvider } from '@/lib/auth';
import { apiFetch } from '@/lib/api';

// Mock the API and Next.js router
vi.mock('@/lib/api', () => ({
  apiFetch: vi.fn(),
}));

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

describe('Authentication Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders login form correctly', () => {
    render(<AuthProvider><LoginPage /></AuthProvider>);
    
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('shows error on invalid credentials', async () => {
    // @ts-expect-error mock resolution
    apiFetch.mockRejectedValue(new Error('Invalid username or password'));

    render(<AuthProvider><LoginPage /></AuthProvider>);
    
    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'wrong' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'pass' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText('Invalid username or password')).toBeInTheDocument();
    });
  });

  it('calls login on success', async () => {
    // @ts-expect-error mock resolution
    apiFetch.mockResolvedValueOnce({ access_token: 'fake-token' });
    // @ts-expect-error mock resolution
    apiFetch.mockResolvedValueOnce({ id: 1, username: 'testuser' });

    render(<AuthProvider><LoginPage /></AuthProvider>);
    
    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'testuser' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'correctpass' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith('/login', expect.objectContaining({ method: 'POST' }));
    });
    
    // AuthProvider should intercept login and fetch user info, pushing to /dashboard
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/dashboard');
    });
    
    expect(localStorage.getItem('access_token')).toBe('fake-token');
  });
});

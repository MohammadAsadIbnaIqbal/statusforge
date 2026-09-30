import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SubscribeForm } from '../app/status/[slug]/SubscribeForm';
import { apiFetch } from '../lib/api';

vi.mock('../lib/api', () => ({
  apiFetch: vi.fn(),
}));

describe('Subscribe Form', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('submits successfully', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ message: 'Success' });
    render(<SubscribeForm slug="acme" />);
    
    const input = screen.getByPlaceholderText('Email address');
    const button = screen.getByRole('button', { name: /subscribe/i });
    
    fireEvent.change(input, { target: { value: 'test@example.com' } });
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith('/status/acme/subscribe', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ email: 'test@example.com' })
      }));
    });
    
    await waitFor(() => {
      expect(screen.getByText('Success')).toBeInTheDocument();
    });
  });

  it('handles duplicate subscription error', async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error('Email already subscribed'));
    render(<SubscribeForm slug="acme" />);
    
    const input = screen.getByPlaceholderText('Email address');
    const button = screen.getByRole('button', { name: /subscribe/i });
    
    fireEvent.change(input, { target: { value: 'test@example.com' } });
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(screen.getByText('This email is already subscribed.')).toBeInTheDocument();
    });
  });
});

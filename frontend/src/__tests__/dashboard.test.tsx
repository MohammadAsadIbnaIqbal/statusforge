import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ServicesPage from '@/app/(dashboard)/services/page';
import IncidentsPage from '@/app/(dashboard)/incidents/page';
import SubscribersPage from '@/app/(dashboard)/subscribers/page';
import { apiFetch } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  apiFetch: vi.fn(),
}));

describe('Dashboard Pages Rendering', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders services list correctly', async () => {
    // @ts-expect-error test mock
    apiFetch.mockResolvedValue([
      { id: 1, name: 'API Server', description: 'desc', current_status: 'OPERATIONAL', is_visible: true, display_order: 1 }
    ]);
    render(<ServicesPage />);
    await waitFor(() => {
      expect(screen.getByText('API Server')).toBeInTheDocument();
      expect(screen.getByText('OPERATIONAL')).toBeInTheDocument();
    });
  });

  it('renders incidents list correctly', async () => {
    // @ts-expect-error test mock
    apiFetch.mockResolvedValue({
      items: [
        { id: 1, title: 'Database Outage', status: 'INVESTIGATING', impact: 'MAJOR', services: [], created_at: '2026-09-29T10:00:00Z' }
      ],
      total: 1, limit: 100, offset: 0
    });
    render(<IncidentsPage />);
    await waitFor(() => {
      expect(screen.getByText('Database Outage')).toBeInTheDocument();
      expect(screen.getByText('INVESTIGATING')).toBeInTheDocument();
    });
  });

  it('renders subscribers list correctly', async () => {
    // @ts-expect-error test mock
    apiFetch.mockResolvedValue([
      { id: 1, email: 'user@example.com', is_confirmed: true, created_at: '2026-09-29T10:00:00Z' }
    ]);
    render(<SubscribersPage />);
    await waitFor(() => {
      expect(screen.getByText('user@example.com')).toBeInTheDocument();
      expect(screen.getByText('Confirmed')).toBeInTheDocument();
    });
  });
});

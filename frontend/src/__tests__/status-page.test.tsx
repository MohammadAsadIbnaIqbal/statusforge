import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import PublicStatusPage from '../app/status/[slug]/page';
import { apiFetch, ApiFetchError } from '../lib/api';


vi.mock('../lib/api', async () => {
  return {
    apiFetch: vi.fn(),
    ApiFetchError: class ApiFetchError extends Error {
      status: number;
      constructor(msg: string, status: number) {
        super(msg);
        this.status = status;
      }
    }
  };
});

vi.mock('next/navigation', () => ({
  notFound: vi.fn(),
}));

const mockStatusData = {
  organization: { name: 'Acme Corp', slug: 'acme' },
  overall_status: 'OPERATIONAL',
  services: [
    { id: 1, name: 'API', status: 'OPERATIONAL', description: 'Core API' }
  ],
  active_incidents: [],
  recent_incidents: []
};

describe('Public Status Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders operational state correctly', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(mockStatusData);
    const UI = await PublicStatusPage({ params: Promise.resolve({ slug: 'acme' }) });
    render(UI);
    expect(screen.getByText('Acme Corp Status')).toBeInTheDocument();
    expect(screen.getAllByText('All Systems Operational')[0]).toBeInTheDocument();
  });

  it('renders degraded state and active incidents', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      ...mockStatusData,
      overall_status: 'PARTIAL_OUTAGE',
      services: [
        { id: 1, name: 'API', status: 'PARTIAL_OUTAGE', description: '' }
      ],
      active_incidents: [
        {
          id: 10,
          title: 'Database connection drop',
          impact: 'MAJOR',
          status: 'INVESTIGATING',
          created_at: '2026-09-29T10:00:00Z',
          resolved_at: null,
          services: [{ id: 1, name: 'API' }],
          updates: [
            {
              status: 'INVESTIGATING',
              message: 'We are looking into this.',
              created_at: '2026-09-29T10:00:00Z'
            }
          ]
        }
      ]
    });
    
    const UI = await PublicStatusPage({ params: Promise.resolve({ slug: 'acme' }) });
    render(UI);
    
    expect(screen.getAllByText('Partial Outage').length).toBeGreaterThan(0);
    expect(screen.getByText('Database connection drop')).toBeInTheDocument();
    expect(screen.getByText('We are looking into this.')).toBeInTheDocument();
  });

  it('handles not found', async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new ApiFetchError('Not found', 404));
    const { notFound } = await import('next/navigation');
    
    try {
      await PublicStatusPage({ params: Promise.resolve({ slug: 'invalid' }) });
    } catch {
      // ignore
    }
    
    expect(notFound).toHaveBeenCalled();
  });

  it('handles 500 error', async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new ApiFetchError('Internal Server Error', 500));
    const { notFound } = await import('next/navigation');
    
    let caughtError;
    try {
      await PublicStatusPage({ params: Promise.resolve({ slug: 'invalid' }) });
    } catch (e: any) /* eslint-disable-line @typescript-eslint/no-explicit-any */ {
      caughtError = e;
    }
    
    expect(caughtError).toBeInstanceOf(ApiFetchError);
    expect(notFound).not.toHaveBeenCalled();
  });

  it('handles network failure', async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new TypeError('Failed to fetch'));
    const { notFound } = await import('next/navigation');
    
    let caughtError;
    try {
      await PublicStatusPage({ params: Promise.resolve({ slug: 'invalid' }) });
    } catch (e: any) /* eslint-disable-line @typescript-eslint/no-explicit-any */ {
      caughtError = e;
    }
    
    expect(caughtError).toBeInstanceOf(TypeError);
    expect(notFound).not.toHaveBeenCalled();
  });
});


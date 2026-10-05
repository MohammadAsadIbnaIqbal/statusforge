import { useCallback } from 'react';
import { useAuth } from '@/lib/auth';
import { apiFetch } from './api';

export function useApi() {
  const { token, activeOrganization } = useAuth();

  const fetchApi = useCallback(async (endpoint: string, options: RequestInit = {}) => {
    return apiFetch(
      endpoint,
      options,
      token || undefined,
      activeOrganization?.id || undefined
    );
  }, [token, activeOrganization]);

  return { fetchApi };
}

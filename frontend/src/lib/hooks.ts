import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from './api';
import { Service, Incident, Subscriber, PaginatedResponse } from '@/types/api';

export function useServices() {
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchServices = useCallback(async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token') || undefined;
      const data = await apiFetch('/services', {}, token);
      setServices(data);
      setError(null);
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
      else setError('Failed to fetch services');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => fetchServices(), 0);
    return () => clearTimeout(timer);
  }, [fetchServices]);

  return { services, loading, error, refetch: fetchServices };
}

export function useIncidents(statusFilter?: string) {
  const [incidents, setIncidents] = useState<PaginatedResponse<Incident> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchIncidents = useCallback(async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token') || undefined;
      let url = '/incidents?limit=100';
      if (statusFilter) url += `&status=${statusFilter}`;
      const data = await apiFetch(url, {}, token);
      setIncidents(data);
      setError(null);
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
      else setError('Failed to fetch incidents');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    const timer = setTimeout(() => fetchIncidents(), 0);
    return () => clearTimeout(timer);
  }, [fetchIncidents]);

  return { incidents, loading, error, refetch: fetchIncidents };
}

export function useSubscribers() {
  const [subscribers, setSubscribers] = useState<Subscriber[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSubscribers = useCallback(async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token') || undefined;
      const data = await apiFetch('/subscribers', {}, token);
      setSubscribers(data);
      setError(null);
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
      else setError('Failed to fetch subscribers');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => fetchSubscribers(), 0);
    return () => clearTimeout(timer);
  }, [fetchSubscribers]);

  return { subscribers, loading, error, refetch: fetchSubscribers };
}

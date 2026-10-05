/* eslint-disable react-hooks/set-state-in-effect */
/* eslint-disable react-hooks/exhaustive-deps */
import { useState, useEffect, useCallback } from 'react';
import { useApi } from './useApi';
import { Service, Incident, Subscriber, PaginatedResponse } from '@/types/api';

export function useServices() {
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { fetchApi } = useApi();

  const fetchServices = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchApi('/services');
      setServices(data);
      setError(null);
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
      else setError('Failed to fetch services');
    } finally {
      setLoading(false);
    }
  }, [fetchApi]);

  useEffect(() => {
    fetchServices();
  }, [fetchServices]);

  return { services, loading, error, refetch: fetchServices };
}

export function useIncidents(statusFilter?: string) {
  const [incidents, setIncidents] = useState<PaginatedResponse<Incident> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { fetchApi } = useApi();

  const fetchIncidents = useCallback(async () => {
    try {
      setLoading(true);
      let url = '/incidents?limit=100';
      if (statusFilter) url += "&status=" + statusFilter;
      const data = await fetchApi(url);
      setIncidents(data);
      setError(null);
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
      else setError('Failed to fetch incidents');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, fetchApi]);

  useEffect(() => {
    fetchIncidents();
  }, [fetchIncidents]);

  return { incidents, loading, error, refetch: fetchIncidents };
}

export function useSubscribers() {
  const [subscribers, setSubscribers] = useState<Subscriber[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { fetchApi } = useApi();

  const fetchSubscribers = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchApi('/subscribers');
      setSubscribers(data);
      setError(null);
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
      else setError('Failed to fetch subscribers');
    } finally {
      setLoading(false);
    }
  }, [fetchApi]);

  useEffect(() => {
    fetchSubscribers();
  }, [fetchSubscribers]);

  return { subscribers, loading, error, refetch: fetchSubscribers };
}

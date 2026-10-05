export interface User {
  id: number;
  email: string;
  display_name: string | null;
  photo_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface Organization {
  id: number;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

export interface Membership {
  user_id: number;
  organization_id: number;
  role: 'OWNER' | 'ADMIN' | 'MEMBER' | 'VIEWER';
  created_at: string;
}

export interface Service {
  id: number;
  name: string;
  description: string;
  current_status: 'OPERATIONAL' | 'DEGRADED_PERFORMANCE' | 'PARTIAL_OUTAGE' | 'MAJOR_OUTAGE' | 'UNDER_MAINTENANCE';
  display_order: number;
  is_visible: boolean;
  created_at: string;
  updated_at: string;
}

export interface IncidentUpdate {
  id: number;
  incident_id: number;
  status: 'INVESTIGATING' | 'IDENTIFIED' | 'MONITORING' | 'RESOLVED';
  message: string;
  created_at: string;
}

export interface Incident {
  id: number;
  title: string;
  status: 'INVESTIGATING' | 'IDENTIFIED' | 'MONITORING' | 'RESOLVED';
  impact: 'NONE' | 'MINOR' | 'MAJOR' | 'CRITICAL';
  services: Service[];
  updates: IncidentUpdate[];
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Subscriber {
  id: number;
  email: string;
  is_confirmed: boolean;
  created_at: string;
}

export interface ApiError {
  message: string;
  errors?: Record<string, string[]>;
}

export interface PublicStatusResponse {
  organization: { name: string; slug: string };
  overall_status: string;
  services: { id: number; name: string; status: string; description: string }[];
  active_incidents: Incident[];
  recent_incidents: Incident[];
}

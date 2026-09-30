export class ApiFetchError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiFetchError';
    this.status = status;
  }
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch(
  endpoint: string,
  options: RequestInit = {},
  token?: string
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = 'Bearer ' + token;
  }

  const response = await fetch(API_BASE_URL + endpoint, {
    ...options,
    headers,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new ApiFetchError(data.detail || "An error occurred", response.status);
  }

  return data;
}

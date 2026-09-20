/**
 * Centralized Axios API Client
 * ─────────────────────────────
 * • Automatically attaches Supabase JWT to every request
 * • On 401, attempts a single token refresh then retries
 * • Normalises API errors to human-readable messages
 * • 2-retry exponential back-off on network failures
 */
import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { supabase } from '@/lib/supabase';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const MAX_RETRIES = 2;
const REQUEST_START = Symbol('requestStart');

type TimedRequestConfig = InternalAxiosRequestConfig & {
  [REQUEST_START]?: number;
  _retryCount?: number;
};

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
});

// ─── Request interceptor: inject JWT ─────────────────────────────────────────
api.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const timedConfig = config as TimedRequestConfig;
  timedConfig[REQUEST_START] = performance.now();
  try {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch {
    // proceed without token if session fetch fails
  }
  return config;
});

// ─── Response interceptor: handle 401, retry, error shaping ──────────────────
api.interceptors.response.use(
  (response) => {
    recordRequestTiming(response.config as TimedRequestConfig, response.status);
    return response;
  },
  async (error: AxiosError) => {
    const config = error.config as TimedRequestConfig;

    // Network / timeout retry with exponential back-off
    if (!error.response && config) {
      config._retryCount = (config._retryCount ?? 0) + 1;
      if (config._retryCount <= MAX_RETRIES) {
        const delay = 500 * 2 ** (config._retryCount - 1);
        await new Promise((r) => setTimeout(r, delay));
        return api(config);
      }
    }

    // 401 → attempt Supabase token refresh then retry once
    if (error.response?.status === 401 && config && !(config as any)._refreshed) {
      try {
        const { data, error: refreshError } = await supabase.auth.refreshSession();
        if (!refreshError && data.session) {
          config.headers = config.headers ?? {};
          config.headers.Authorization = `Bearer ${data.session.access_token}`;
          (config as any)._refreshed = true;
          return api(config);
        }
      } catch {
        // refresh failed — fall through to normal error handling
      }
    }

    // Shape the error for consumers
    const apiError = normalizeApiError(error);
    recordRequestTiming(config, error.response?.status ?? 0);
    return Promise.reject(apiError);
  },
);

function recordRequestTiming(config: TimedRequestConfig | undefined, status: number) {
  if (!import.meta.env.DEV || !config?.[REQUEST_START]) return;

  const durationMs = performance.now() - config[REQUEST_START];
  console.debug('[api]', config.method?.toUpperCase(), config.url, `${durationMs.toFixed(1)}ms`, status);
}

function normalizeApiError(error: AxiosError): Error {
  if (!error.response) {
    return new Error('Network error. Please check your connection and try again.');
  }
  const status = error.response.status;
  const data = error.response.data as Record<string, unknown>;
  const detail =
    typeof data?.detail === 'string'
      ? data.detail
      : typeof data?.message === 'string'
        ? data.message
        : undefined;

  const statusMessages: Record<number, string> = {
    400: detail ?? 'Bad request. Please check your input.',
    401: 'Authentication required. Please sign in again.',
    403: 'You do not have permission to perform this action.',
    404: detail ?? 'The requested resource was not found.',
    409: detail ?? 'A conflict occurred. The resource may already exist or be in use.',
    422: detail ?? 'Validation error. Please check your input.',
    429: 'Too many requests. Please slow down.',
    500: 'Internal server error. Please try again later.',
    502: 'Server is temporarily unavailable. Please try again later.',
    503: 'Service unavailable. Please try again later.',
  };

  const message = statusMessages[status] ?? detail ?? `Unexpected error (${status}).`;
  const err = new Error(message);
  (err as any).status = status;
  (err as any).detail = detail;
  return err;
}

export default api;

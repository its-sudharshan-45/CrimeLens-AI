import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateString?: string | Date | null, options?: Intl.DateTimeFormatOptions): string {
  if (!dateString) return '—';
  const d = new Date(dateString);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('en-US', options ?? {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

export function formatCount(value?: number | null, loading = false): string {
  if (loading) return '—';
  if (value === undefined || value === null) return '0';
  return value.toLocaleString();
}

export function formatPercent(value?: number | null, loading = false, digits = 1): string {
  if (loading) return '—';
  if (value === undefined || value === null) return '—';
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatMs(value?: number | null, loading = false): string {
  if (loading) return '—';
  if (value === undefined || value === null) return '—';
  return `${Math.round(value)} ms`;
}

export function formatDateTime(dateString?: string | Date | null): string {
  if (!dateString) return '—';
  const d = new Date(dateString);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleString('en-US', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

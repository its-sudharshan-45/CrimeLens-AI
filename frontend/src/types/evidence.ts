import type { PaginationParams } from './api';

export type EvidenceType =
  | 'IMAGE' | 'VIDEO' | 'AUDIO' | 'DOCUMENT' | 'SPREADSHEET'
  | 'ARCHIVE' | 'OTHER';

export interface Evidence {
  id: string;
  report_id: string;
  uploader_id: string;
  uploader?: { id: string; email: string; full_name?: string };
  file_name: string;
  file_size: number;
  content_type: string;
  storage_path: string;
  description?: string;
  evidence_type?: EvidenceType;
  created_at: string;
  updated_at: string;
}

export interface EvidenceUpdate {
  description?: string;
}

export interface EvidenceFilters extends PaginationParams {
  report_id: string;
}

export function getEvidenceIcon(contentType: string): string {
  if (contentType.startsWith('image/')) return 'image';
  if (contentType.startsWith('video/')) return 'video';
  if (contentType.startsWith('audio/')) return 'audio';
  if (contentType.includes('pdf')) return 'pdf';
  if (contentType.includes('word') || contentType.includes('document')) return 'doc';
  if (contentType.includes('excel') || contentType.includes('spreadsheet')) return 'sheet';
  if (contentType.includes('zip') || contentType.includes('archive') || contentType.includes('tar')) return 'archive';
  return 'file';
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / 1024 ** i).toFixed(1)} ${units[i]}`;
}

import api from '@/lib/api';
import type { Evidence, EvidenceUpdate } from '@/types/evidence';

const BASE = '/evidence';

export const evidenceService = {
  async getByReport(
    reportId: string,
    page = 1,
    pageSize = 20,
  ): Promise<{ items: Evidence[]; total: number; page: number; page_size: number; total_pages: number }> {
    const { data } = await api.get(`${BASE}/crime-reports/${reportId}/evidence`, {
      params: { page, page_size: pageSize },
    });
    return data;
  },

  async getById(id: string): Promise<Evidence> {
    const { data } = await api.get<Evidence>(`${BASE}/${id}`);
    return data;
  },

  async upload(
    reportId: string,
    file: File,
    description?: string,
    onProgress?: (pct: number) => void,
  ): Promise<Evidence> {
    const form = new FormData();
    form.append('report_id', reportId);
    form.append('file', file);
    if (description) form.append('description', description);

    const { data } = await api.post<Evidence>(`${BASE}/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (evt) => {
        if (evt.total && onProgress) {
          onProgress(Math.round((evt.loaded / evt.total) * 100));
        }
      },
    });
    return data;
  },

  async getDownloadUrl(id: string): Promise<string> {
    const { data } = await api.get<{ download_url: string }>(`${BASE}/${id}/download`);
    return data.download_url;
  },

  async update(id: string, payload: EvidenceUpdate): Promise<Evidence> {
    const { data } = await api.patch<Evidence>(`${BASE}/${id}`, payload);
    return data;
  },

  async remove(id: string): Promise<void> {
    await api.delete(`${BASE}/${id}`);
  },
};

import api from '@/lib/api';
import type {
  Investigation,
  InvestigationCreate,
  InvestigationStatusUpdate,
  InvestigationAssign,
  InvestigationNote,
  InvestigationNoteCreate,
  InvestigationNoteUpdate,
  InvestigationTimeline,
  InvestigationFilters,
} from '@/types/investigation';

const BASE = '/investigations';

export const investigationService = {
  async list(
    filters: InvestigationFilters = {},
  ): Promise<{ items: Investigation[]; total: number; page: number; page_size: number; total_pages: number }> {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, v]) => v !== '' && v !== undefined && v !== null),
    );
    const { data } = await api.get(BASE, { params });
    return data;
  },

  async getById(id: string): Promise<Investigation> {
    const { data } = await api.get<Investigation>(`${BASE}/${id}`);
    return data;
  },

  async create(payload: InvestigationCreate): Promise<Investigation> {
    const { data } = await api.post<Investigation>(BASE, payload);
    return data;
  },

  async updateStatus(id: string, payload: InvestigationStatusUpdate): Promise<Investigation> {
    const { data } = await api.patch<Investigation>(`${BASE}/${id}/status`, payload);
    return data;
  },

  async assign(id: string, payload: InvestigationAssign): Promise<Investigation> {
    const { data } = await api.post<Investigation>(`${BASE}/${id}/assign`, payload);
    return data;
  },

  async close(id: string): Promise<Investigation> {
    const { data } = await api.post<Investigation>(`${BASE}/${id}/close`);
    return data;
  },

  async archive(id: string): Promise<Investigation> {
    const { data } = await api.post<Investigation>(`${BASE}/${id}/archive`);
    return data;
  },

  async getTimeline(id: string): Promise<InvestigationTimeline[]> {
    const { data } = await api.get<InvestigationTimeline[]>(`${BASE}/${id}/timeline`);
    return data;
  },

  async getNotes(
    id: string,
    page = 1,
    pageSize = 20,
  ): Promise<{ items: InvestigationNote[]; total: number; page: number; page_size: number; total_pages: number }> {
    const { data } = await api.get(`${BASE}/${id}/notes`, {
      params: { page, page_size: pageSize },
    });
    return data;
  },

  async addNote(id: string, payload: InvestigationNoteCreate): Promise<InvestigationNote> {
    const { data } = await api.post<InvestigationNote>(`${BASE}/${id}/notes`, payload);
    return data;
  },

  async updateNote(noteId: string, payload: InvestigationNoteUpdate): Promise<InvestigationNote> {
    const { data } = await api.patch<InvestigationNote>(`${BASE}/notes/${noteId}`, payload);
    return data;
  },
};

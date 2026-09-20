import api from '@/lib/api';
import type { PaginatedResponse } from '@/types/api';
import type {
  CrimeCategory,
  CrimeCategoryCreate,
  CrimeCategoryUpdate,
  CrimeCategoryFilters,
} from '@/types/crimeCategory';

const BASE = '/crime-categories';

export const crimeCategoryService = {
  async list(filters: CrimeCategoryFilters = {}): Promise<PaginatedResponse<CrimeCategory>> {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, v]) => v !== '' && v !== undefined && v !== null),
    );
    const { data } = await api.get<PaginatedResponse<CrimeCategory>>(BASE, { params });
    return data;
  },

  async getById(id: string): Promise<CrimeCategory> {
    const { data } = await api.get<CrimeCategory>(`${BASE}/${id}`);
    return data;
  },

  async create(payload: CrimeCategoryCreate): Promise<CrimeCategory> {
    const { data } = await api.post<CrimeCategory>(BASE, payload);
    return data;
  },

  async update(id: string, payload: CrimeCategoryUpdate): Promise<CrimeCategory> {
    const { data } = await api.patch<CrimeCategory>(`${BASE}/${id}`, payload);
    return data;
  },

  async remove(id: string): Promise<void> {
    await api.delete(`${BASE}/${id}`);
  },
};

import api from '@/lib/api';
import type { PaginatedResponse } from '@/types/api';
import type {
  CrimeLocation,
  CrimeLocationCreate,
  CrimeLocationUpdate,
  CrimeLocationFilters,
} from '@/types/crimeLocation';

const BASE = '/crime-locations';

export const crimeLocationService = {
  async list(filters: CrimeLocationFilters = {}): Promise<PaginatedResponse<CrimeLocation>> {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, v]) => v !== '' && v !== undefined && v !== null),
    );
    const { data } = await api.get<PaginatedResponse<CrimeLocation>>(BASE, { params });
    return data;
  },

  async getById(id: string): Promise<CrimeLocation> {
    const { data } = await api.get<CrimeLocation>(`${BASE}/${id}`);
    return data;
  },

  async create(payload: CrimeLocationCreate): Promise<CrimeLocation> {
    const { data } = await api.post<CrimeLocation>(BASE, payload);
    return data;
  },

  async update(id: string, payload: CrimeLocationUpdate): Promise<CrimeLocation> {
    const { data } = await api.patch<CrimeLocation>(`${BASE}/${id}`, payload);
    return data;
  },

  async remove(id: string): Promise<void> {
    await api.delete(`${BASE}/${id}`);
  },
};

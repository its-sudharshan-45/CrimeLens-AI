import api from '@/lib/api';
import type { PaginatedResponse } from '@/types/api';
import type {
  CrimeReport,
  CrimeReportCreate,
  CrimeReportUpdate,
  CrimeReportFilters,
} from '@/types/crimeReport';

const BASE = '/crime-reports';

export const crimeReportService = {
  async list(filters: CrimeReportFilters = {}): Promise<PaginatedResponse<CrimeReport>> {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, v]) => v !== '' && v !== undefined && v !== null),
    );
    const { data } = await api.get<PaginatedResponse<CrimeReport>>(BASE, { params });
    return data;
  },

  async getById(id: string): Promise<CrimeReport> {
    const { data } = await api.get<CrimeReport>(`${BASE}/${id}`);
    return data;
  },

  async create(payload: CrimeReportCreate): Promise<CrimeReport> {
    const { data } = await api.post<CrimeReport>(BASE, payload);
    return data;
  },

  async update(id: string, payload: CrimeReportUpdate): Promise<CrimeReport> {
    const { data } = await api.patch<CrimeReport>(`${BASE}/${id}`, payload);
    return data;
  },

  async remove(id: string): Promise<void> {
    await api.delete(`${BASE}/${id}`);
  },
};

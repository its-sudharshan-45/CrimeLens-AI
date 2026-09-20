import api from '@/lib/api';
import type {
  ModelListResponse,
  ModelVersionInfo,
  AnalyticsResponse,
  DriftStatusResponse,
  DriftReportResponse,
  SystemStatusResponse,
} from '@/types/ai';

const BASE = '/mlops';

export const mlopsService = {
  async listModels(): Promise<ModelListResponse> {
    const { data } = await api.get<ModelListResponse>(`${BASE}/models`);
    return data;
  },

  async getCurrentModel(): Promise<ModelVersionInfo> {
    const { data } = await api.get<ModelVersionInfo>(`${BASE}/models/current`);
    return data;
  },

  async getAnalytics(): Promise<AnalyticsResponse> {
    const { data } = await api.get<AnalyticsResponse>(`${BASE}/analytics`);
    return data;
  },

  async getDriftStatus(): Promise<DriftStatusResponse> {
    const { data } = await api.get<DriftStatusResponse>(`${BASE}/drift`);
    return data;
  },

  async getDriftReport(): Promise<DriftReportResponse> {
    const { data } = await api.get<DriftReportResponse>(`${BASE}/drift/report`);
    return data;
  },

  async getSystemStatus(): Promise<SystemStatusResponse> {
    const { data } = await api.get<SystemStatusResponse>(`${BASE}/system`);
    return data;
  },
};

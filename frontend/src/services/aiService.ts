import api from '@/lib/api';
import type {
  ForecastRequest,
  ForecastResponse,
  ModelHealthResponse,
  ModelMetadataResponse,
  ScopeListResponse,
  ScopeType,
} from '@/types/ai';

const BASE = '/ai';

export const aiService = {
  /** 7-day GRU crime-count forecast for a city or crime-type scope. */
  async forecast(payload: ForecastRequest): Promise<ForecastResponse> {
    const { data } = await api.post<ForecastResponse>(`${BASE}/forecast`, payload);
    return data;
  },

  /** Every supported forecasting scope (all cities + all crime types). */
  async getScopes(scopeType?: ScopeType): Promise<ScopeListResponse> {
    const { data } = await api.get<ScopeListResponse>(`${BASE}/scopes`, {
      params: scopeType ? { scope_type: scopeType } : undefined,
    });
    return data;
  },

  async getModelMetadata(): Promise<ModelMetadataResponse> {
    const { data } = await api.get<ModelMetadataResponse>(`${BASE}/models`);
    return data;
  },

  async getHealthStatus(): Promise<ModelHealthResponse> {
    const { data } = await api.get<ModelHealthResponse>(`${BASE}/health`);
    return data;
  },
};

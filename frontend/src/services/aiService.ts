import api from '@/lib/api';
import type {
  LocationCatalogResponse,
  ModelHealthResponse,
  RiskPredictionRequest,
  RiskPredictionResponse,
} from '@/types/ai';

const BASE = '/ai';

export const aiService = {
  /** State -> district catalog backed by the trained model's city scopes. */
  async getLocations(): Promise<LocationCatalogResponse> {
    const { data } = await api.get<LocationCatalogResponse>(`${BASE}/locations`);
    return data;
  },

  /** Run a genuine district risk prediction from the trained GRU forecast. */
  async predictRisk(payload: RiskPredictionRequest): Promise<RiskPredictionResponse> {
    const { data } = await api.post<RiskPredictionResponse>(`${BASE}/risk`, payload);
    return data;
  },

  /** Model load status (used for a small availability badge). */
  async getHealth(): Promise<ModelHealthResponse> {
    const { data } = await api.get<ModelHealthResponse>(`${BASE}/health`);
    return data;
  },
};

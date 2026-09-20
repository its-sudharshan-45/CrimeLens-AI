import api from '@/lib/api';
import type {
  CrimePredictionRequest,
  CrimePredictionResponse,
  ForecastRequest,
  ForecastResponse,
  ExplainabilityRequest,
  ExplainabilityResponse,
  BatchPredictionResponse,
  ModelHealthResponse,
  ModelMetadataResponse,
} from '@/types/ai';

const BASE = '/ai';

export const aiService = {
  async predict(payload: CrimePredictionRequest): Promise<CrimePredictionResponse> {
    const { data } = await api.post<CrimePredictionResponse>(`${BASE}/predict`, payload);
    return data;
  },

  async forecast(payload: ForecastRequest): Promise<ForecastResponse> {
    const { data } = await api.post<ForecastResponse>(`${BASE}/forecast`, payload);
    return data;
  },

  async explain(payload: ExplainabilityRequest): Promise<ExplainabilityResponse> {
    const { data } = await api.post<ExplainabilityResponse>(`${BASE}/explain`, payload);
    return data;
  },

  async batchPredict(records: CrimePredictionRequest[]): Promise<BatchPredictionResponse> {
    const { data } = await api.post<BatchPredictionResponse>(`${BASE}/batch-predict`, { records });
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

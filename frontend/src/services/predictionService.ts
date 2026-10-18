/**
 * frontend/src/services/predictionService.ts
 * ==========================================
 * Client service for the remaining Prediction API endpoints.
 *   - getHotspots(): DEPRECATED 410 stub (CNN removed 2026-10-16)
 *   - getPredictionHistory(): paginated audit history
 *   - getPredictionStats(): aggregate observability metrics
 *
 * Live crime forecasting is served by `aiService.forecast()`.
 */

import api from '@/lib/api';
import type {
  HotspotPredictionRequest,
  PredictionHistoryResponse,
  PredictionStatsResponse,
} from '@/types/prediction';

const BASE = '/predict';

export const predictionService = {
  /**
   * DEPRECATED (CNN removed 2026-10-16). The backend returns HTTP 410 Gone
   * because the crime dataset is tabular, not image data. Retained so the
   * deprecation contract is explicit; historical records remain available via
   * getPredictionHistory().
   * @deprecated
   */
  async getHotspots(payload?: HotspotPredictionRequest): Promise<unknown> {
    const { data } = await api.post(`${BASE}/hotspots`, payload ?? { top_n: 5, crime_type: 'All' });
    return data;
  },

  /** Fetches paginated prediction history records from the database. */
  async getPredictionHistory(page = 1, pageSize = 20, predictionType?: string): Promise<PredictionHistoryResponse> {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (predictionType) params.append('prediction_type', predictionType);
    const { data } = await api.get<PredictionHistoryResponse>(`${BASE}/history?${params.toString()}`);
    return data;
  },

  /** Fetches real aggregate prediction observability metrics. */
  async getPredictionStats(): Promise<PredictionStatsResponse> {
    const { data } = await api.get<PredictionStatsResponse>(`${BASE}/stats`);
    return data;
  },
};

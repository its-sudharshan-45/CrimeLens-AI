/**
 * frontend/src/services/predictionService.ts
 * ==========================================
 * Client service for Phase 5 Prediction API endpoints:
 *  - getHotspots(): Phase 4 CNN Hotspot Model
 *  - getTemporalRisk(): Phase 3 GRU Temporal Forecaster
 *  - getInvestigationLeads(): Pattern-Based Investigative Assistant
 */

import api from '@/lib/api';
import type {
  HotspotPredictionRequest,
  HotspotPredictionResponse,
  TemporalRiskRequest,
  TemporalRiskResponse,
  InvestigationLeadRequest,
  InvestigationLeadResponse,
} from '@/types/prediction';

const BASE = '/predict';

export const predictionService = {
  /**
   * Evaluates all 29 cities and retrieves top-N crime hotspots using Phase 4 CNN model.
   */
  async getHotspots(payload?: HotspotPredictionRequest): Promise<HotspotPredictionResponse> {
    const { data } = await api.post<HotspotPredictionResponse>(
      `${BASE}/hotspots`,
      payload ?? { top_n: 5, crime_type: 'All' }
    );
    return data;
  },

  /**
   * Forecasts multi-day crime activity trajectory using Phase 3 GRU model.
   */
  async getTemporalRisk(payload: TemporalRiskRequest): Promise<TemporalRiskResponse> {
    const { data } = await api.post<TemporalRiskResponse>(
      `${BASE}/temporal-risk`,
      payload
    );
    return data;
  },

  /**
   * Generates pattern-based investigative priorities for an investigator without individual profiling.
   */
  async getInvestigationLeads(payload: InvestigationLeadRequest): Promise<InvestigationLeadResponse> {
    const { data } = await api.post<InvestigationLeadResponse>(
      `${BASE}/investigation-leads`,
      payload
    );
    return data;
  },

  /**
   * Fetches paginated prediction history records from the database.
   */
  async getPredictionHistory(page = 1, pageSize = 20, predictionType?: string) {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (predictionType) params.append('prediction_type', predictionType);
    const { data } = await api.get<import('@/types/prediction').PredictionHistoryResponse>(
      `${BASE}/history?${params.toString()}`
    );
    return data;
  },
};

/**
 * TypeScript interfaces for the legacy CrimeLens AI prediction API.
 *
 * Live forecasting now lives at POST /api/v1/ai/forecast. This module mirrors
 * the remaining routes in `backend/app/api/v1/predictions.py`:
 *   - POST /predict/hotspots — DEPRECATED 410 Gone (CNN removed 2026-10-16)
 *   - GET  /predict/history  — paginated prediction audit history
 *   - GET  /predict/stats    — aggregate prediction observability metrics
 */

export interface HotspotPredictionRequest {
  top_n?: number;
  crime_type?: string;
}

export interface PredictionHistoryItem {
  id: string;
  prediction_label: string;
  prediction_type: string;
  confidence_score: number;
  model_name: string;
  model_version: string;
  execution_time_ms: number;
  created_at: string;
}

export interface PredictionHistoryResponse {
  items: PredictionHistoryItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface PredictionStatsResponse {
  total_predictions: number;
  predictions_today: number;
  avg_execution_time_ms: number;
  predictions_by_model: Record<string, number>;
  predictions_by_type: Record<string, number>;
  active_models: string[];
}

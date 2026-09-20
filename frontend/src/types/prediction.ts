/**
 * TypeScript Interfaces for CrimeLens AI Prediction API (Phase 5)
 * Mirrors backend app/schemas/prediction.py
 */

export interface HotspotPredictionRequest {
  top_n?: number;
  crime_type?: string;
}

export interface HotspotItem {
  rank: number;
  city: string;
  predicted_crimes: number;
  risk_score: number;
  risk_level: 'High' | 'Medium' | 'Low';
  confidence_score: number;
}

export interface HotspotPredictionResponse {
  success: boolean;
  prediction_type: string;
  forecast_horizon_days: number;
  total_cities_evaluated?: number;
  filter_crime_type?: string;
  hotspots: HotspotItem[];
  confidence_metric?: string;
  disclaimer: string;
}

export interface TemporalRiskRequest {
  city: string;
}

export interface TemporalForecastDay {
  day: number;
  predicted_crimes: number;
  confidence_score: number;
  lower_bound_95?: number;
  upper_bound_95?: number;
}

export interface HistoricalDay {
  day_label: string;
  crime_count: number;
}

export interface TemporalRiskResponse {
  success: boolean;
  prediction_type: string;
  prediction_scope: string;
  target_city?: string;
  forecast_horizon_days: number;
  forecast: TemporalForecastDay[];
  historical_context?: HistoricalDay[];
  uncertainty_method?: string;
  disclaimer: string;
}

export interface InvestigationLeadRequest {
  city: string;
  crime_type?: string;
  risk_level?: string;
}

export interface InvestigationLead {
  priority: number;
  category: string;
  description: string;
  reason: string;
  confidence_score: number;
}

export interface InvestigationLeadResponse {
  success: boolean;
  prediction_type: string;
  city?: string;
  crime_type?: string;
  risk_assessment?: string;
  leads: InvestigationLead[];
  disclaimer: string;
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

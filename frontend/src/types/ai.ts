/**
 * TypeScript interfaces for CrimeLens AI.
 *
 * The project ships a SINGLE deep-learning model — the GRU crime-count
 * forecaster — served at POST /api/v1/ai/forecast. These types mirror
 * `backend/app/schemas/ai.py` and `backend/app/schemas/mlops.py`.
 */

// ─── Forecasting scopes ─────────────────────────────────────────────────────

export type ScopeType = 'city' | 'crime_type';

export interface ScopeInfo {
  key: string;
  scope_type: ScopeType;
  display_name: string;
}

export interface ScopeListResponse {
  scopes: ScopeInfo[];
  count: number;
}

// ─── Forecast ───────────────────────────────────────────────────────────────

export interface ForecastRequest {
  scope_type: ScopeType;
  scope_value: string;
}

export interface HistoricalPoint {
  date: string;
  count: number;
}

export interface ForecastDay {
  day: number;
  date: string;
  predicted_count: number;
  lower_bound_95: number;
  upper_bound_95: number;
}

export interface ActualVsPredictedPoint {
  date: string;
  actual: number;
  predicted: number;
}

export interface RegressionMetrics {
  MAE: number;
  RMSE: number;
  WAPE: number;
  sMAPE: number;
  R2: number;
  n_observations: number;
}

export interface ForecastResponse {
  success: boolean;
  scope_key: string;
  scope_type: ScopeType;
  scope_display_name: string;
  model_name: string;
  model_version: string;
  sequence_length: number;
  forecast_horizon_days: number;
  last_observed_date: string;
  historical: HistoricalPoint[];
  forecast: ForecastDay[];
  actual_vs_predicted: ActualVsPredictedPoint[];
  scope_test_metrics: Partial<RegressionMetrics>;
  test_metrics: {
    model?: RegressionMetrics;
    persistence_baseline?: RegressionMetrics;
    model_beats_baseline_MAE?: boolean;
  };
  per_horizon_metrics: Record<string, unknown>;
  evaluation_summary: Record<string, unknown>;
  uncertainty_method?: string | null;
  disclaimer: string;
  timestamp: string;
}

// ─── Model Health & Metadata ────────────────────────────────────────────────

export interface ModelHealthResponse {
  status: string;
  model_name: string;
  loaded: boolean;
  device: string;
  registry_dir?: string | null;
  n_scopes: number;
  error?: string | null;
}

export interface ModelMetadataResponse {
  version: string;
  primary_model: string;
  framework?: string | null;
  device?: string | null;
  seed?: number | null;
  seq_len?: number | null;
  forecast_horizon?: number | null;
  n_features?: number | null;
  n_scopes?: number | null;
  dataset_rows?: number | null;
  dataset_hash_md5?: string | null;
  test_mae?: number | null;
  test_rmse?: number | null;
  test_wape?: number | null;
  persistence_mae?: number | null;
  saved_at?: string | null;
}

// ─── MLOps – Model Registry ─────────────────────────────────────────────────

export interface ModelVersionInfo {
  model_name: string;
  version: string;
  training_date?: string | null;
  dataset_hash: string;
  dataset_version?: string | null;
  framework_version: string;
  accuracy_metrics: Record<string, number>;
  metrics: Record<string, unknown>;
  status: 'Active' | 'Archived';
  artifact_path?: string | null;
}

export interface ModelListResponse {
  models: ModelVersionInfo[];
  count: number;
}

// ─── MLOps – Analytics ──────────────────────────────────────────────────────

export interface AnalyticsSummary {
  total_predictions: number;
  predictions_today: number;
  predictions_this_month: number;
  average_confidence: number;
  average_inference_latency_ms: number;
  most_predicted_crime_domain?: string | null;
  human_review_count: number;
  low_confidence_count: number;
}

export interface AnalyticsResponse {
  summary: AnalyticsSummary;
  prediction_distribution: Record<string, number>;
  model_usage: Record<string, unknown>[];
  top_confidence_predictions: Record<string, unknown>[];
  low_confidence_predictions: Record<string, unknown>[];
  daily_prediction_trend: Record<string, unknown>[];
  monthly_prediction_trend: Record<string, unknown>[];
  charts: Record<string, unknown>;
}

// ─── MLOps – Drift ──────────────────────────────────────────────────────────

export type DriftLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export interface DriftComponent {
  score: number;
  level: DriftLevel;
  affected_features: string[];
}

export interface DriftStatusResponse {
  drift_score: number;
  overall_level: DriftLevel;
  feature_drift: DriftComponent;
  confidence_drift: Record<string, unknown>;
  prediction_distribution_drift: Record<string, unknown>;
  sample_size: number;
  warnings: string[];
  timestamp: string;
}

export interface DriftReportResponse {
  drift_score: number;
  drift_level: DriftLevel;
  drift_type: string[];
  affected_features: string[];
  recommendation: string;
  warnings: string[];
  timestamp: string;
  details: Record<string, unknown>;
}

// ─── MLOps – System Status ──────────────────────────────────────────────────

export interface SystemStatusResponse {
  api_status: string;
  database_status: string;
  database_detail: string;
  supabase_status: string;
  supabase_detail: string;
  model_status: string;
  model_errors: string[];
  registry_status: string;
  registry_detail: string;
  active_version?: string | null;
  memory_usage_mb?: number | null;
  cpu_usage_percent?: number | null;
  uptime_seconds: number;
  project_root: string;
}

// ─── UI helpers ─────────────────────────────────────────────────────────────

export function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

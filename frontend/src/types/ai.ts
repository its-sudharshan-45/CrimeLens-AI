/**
 * TypeScript interfaces for CrimeLens AI – Phase 8
 * Mirrors backend app/schemas/ai.py and app/schemas/mlops.py exactly.
 */

// ─── AI Prediction ─────────────────────────────────────────────────────────

export interface CrimePredictionRequest {
  city: string;
  crime_description: string;
  victim_age: number;
  victim_gender: string;
  weapon_used?: string;
  date_of_occurrence: string;   // dd-mm-yyyy HH:MM
  time_of_occurrence: string;   // dd-mm-yyyy HH:MM
  date_reported?: string | null;
  case_closed?: string;         // "Yes" | "No"
  crime_code?: number;
}

export interface CrimePredictionResponse {
  prediction_id: string | null;
  predicted_domain: string;
  domain_code: number;
  confidence_score: number;
  probabilities: Record<string, number>;
  model_name: string;
  model_version: string;
  execution_time_ms: number;
  timestamp: string;
}

// ─── Forecasting ────────────────────────────────────────────────────────────

export interface ForecastRequest {
  horizon: 7 | 30 | 90;
  recent_sequence?: number[] | null;
}

export interface ForecastResponse {
  horizon: number;
  forecast_dates: string[];
  predicted_counts: number[];
  total_projected_incidents: number;
  model_name: string;
  model_version: string;
  execution_time_ms: number;
}

// ─── Embedding ──────────────────────────────────────────────────────────────

export interface EmbeddingResponse {
  embedding_vector: number[];
  embedding_dim: number;
  l2_norm: number;
  model_name: string;
}

// ─── Explainability (XAI) ───────────────────────────────────────────────────

export interface FeatureAttribution {
  feature_name: string;
  attribution_score: number;
}

export interface ExplainabilityRequest {
  sample_record: CrimePredictionRequest;
  target_class?: number;
}

export interface ExplainabilityResponse {
  predicted_domain: string;
  confidence_score: number;
  top_contributing_features: FeatureAttribution[];
  saliency_scores: FeatureAttribution[];
  model_name: string;
  method: string;
}

// ─── Batch Prediction ───────────────────────────────────────────────────────

export interface BatchPredictionResponse {
  total_records: number;
  predictions: CrimePredictionResponse[];
  batch_execution_time_ms: number;
}

// ─── Model Health & Metadata ────────────────────────────────────────────────

export interface ModelHealthResponse {
  status: string;
  device: string;
  models_loaded: Record<string, boolean>;
  warmup_complete: boolean;
}

export interface ModelMetadataResponse {
  version: string;
  framework: string;
  flagship_model: string;
  forecaster_model: string;
  embedding_dim: number;
  dataset_rows: number;
  dataset_hash_md5: string;
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

// ─── Derived / UI helpers ───────────────────────────────────────────────────

export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export function confidenceToRisk(confidence: number): RiskLevel {
  if (confidence >= 0.85) return 'CRITICAL';
  if (confidence >= 0.65) return 'HIGH';
  if (confidence >= 0.40) return 'MEDIUM';
  return 'LOW';
}

export function formatConfidence(score: number): string {
  return `${(score * 100).toFixed(1)}%`;
}

export function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

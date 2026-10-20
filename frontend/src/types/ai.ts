/**
 * Types for the district crime-risk prediction API.
 *
 * The backend maps each dataset city scope to an Indian state/district and
 * derives the risk index from the trained GRU forecast. These types mirror
 * `backend/app/schemas/ai.py`.
 */

export type RiskCategory = 'Low' | 'Medium' | 'High';

export type ModelCoverage = 'dataset' | 'proxy';

export interface DistrictLocation {
  district: string;
  /** Dataset city whose trained scope backs this district (direct or proxy). */
  city: string;
  scope_key: string;
  /** True when the district is one of the dataset's city scopes. */
  model_supported: boolean;
  coverage: ModelCoverage;
}

export interface StateLocations {
  state: string;
  districts: DistrictLocation[];
}

export interface LocationCatalogResponse {
  states: StateLocations[];
  /** All officially recognised districts (789). */
  district_count: number;
  /** All 28 States and 8 Union Territories. */
  state_count: number;
  /** Districts with their own dataset city scope (28 unique districts). */
  model_district_count: number;
}

export interface RiskPredictionRequest {
  state: string;
  district: string;
}

export interface RiskForecastDay {
  day: number;
  date: string;
  predicted_count: number;
  lower_bound_95: number;
  upper_bound_95: number;
}

export interface RegressionMetrics {
  MAE?: number;
  RMSE?: number;
  WAPE?: number;
  sMAPE?: number;
  R2?: number;
  n_observations?: number;
}

export interface RiskPredictionResponse {
  success: boolean;
  state: string;
  district: string;
  city: string;
  scope_key: string;
  model_coverage: ModelCoverage;
  proxy_city: string | null;
  risk_percentage: number;
  risk_category: RiskCategory;
  risk_lower_bound: number;
  risk_upper_bound: number;
  risk_method: string;
  predicted_daily_average: number;
  predicted_7_day_total: number;
  prediction_interval_95: {
    daily_lower: number;
    daily_upper: number;
  };
  peak_predicted_daily_average: number;
  district_rank: number | null;
  district_count: number;
  historical_incidents: number;
  historical_daily_average: number;
  last_observed_date: string;
  model_name: string;
  model_version: string;
  model_test_metrics: RegressionMetrics;
  persistence_test_metrics: RegressionMetrics;
  forecast: RiskForecastDay[];
  uncertainty_method?: string | null;
  disclaimer: string;
  timestamp: string;
}

export interface ModelHealthResponse {
  status: string;
  model_name: string;
  loaded: boolean;
  device: string;
  registry_dir?: string | null;
  n_scopes: number;
  error?: string | null;
}

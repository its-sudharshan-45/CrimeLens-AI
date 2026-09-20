export type AuditCategory =
  | 'AUTH'
  | 'AI'
  | 'EVIDENCE'
  | 'INVESTIGATION'
  | 'ADMIN'
  | 'SYSTEM';

export type AuditStatus = 'SUCCESS' | 'FAILURE' | 'WARNING' | 'DENIED';

export interface AuditLogRecord {
  id: string;
  timestamp: string;
  user_id: string;
  user_email: string;
  action: string;
  category: AuditCategory;
  ip_address: string;
  user_agent: string;
  browser: string;
  os: string;
  status: AuditStatus;
  details?: Record<string, any>;
  execution_time_ms?: number;
}

export interface AuditFilterParams {
  search?: string;
  category?: AuditCategory | 'ALL';
  status?: AuditStatus | 'ALL';
  startDate?: string;
  endDate?: string;
}

export type TimelineCategory =
  | 'user_login'
  | 'user_logout'
  | 'crime_created'
  | 'evidence_uploaded'
  | 'prediction_generated'
  | 'model_used'
  | 'investigation_updated'
  | 'settings_modified'
  | 'system_event';

export interface ActivityTimelineItem {
  id: string;
  timestamp: string;
  title: string;
  category: TimelineCategory;
  actor_name: string;
  actor_email: string;
  actor_avatar?: string;
  description: string;
  metadata?: Record<string, any>;
  status: 'info' | 'success' | 'warning' | 'error';
}

export interface SecurityOverviewMetrics {
  successful_logins_24h: number;
  failed_login_attempts_24h: number;
  active_sessions_count: number;
  locked_accounts_count: number;
  password_reset_requests_24h: number;
  unauthorized_access_attempts_24h: number;
  api_auth_failures_24h: number;
  suspicious_activities_count: number;
}

export interface SecurityAlertItem {
  id: string;
  timestamp: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  description: string;
  source_ip: string;
  location?: string;
  user_email?: string;
  status: 'OPEN' | 'INVESTIGATING' | 'RESOLVED' | 'DISMISSED';
}

export interface UserSessionRecord {
  id: string;
  user_id: string;
  user_email: string;
  user_name: string;
  device: string;
  browser: string;
  os: string;
  ip_address: string;
  location: string;
  login_time: string;
  last_activity: string;
  is_current: boolean;
  status: 'ACTIVE' | 'IDLE' | 'EXPIRED';
}

export interface ServiceStatusItem {
  name: string;
  category: 'API' | 'Database' | 'AI Serving' | 'Storage' | 'Auth';
  status: 'HEALTHY' | 'DEGRADED' | 'DOWN';
  latency_ms: number;
  uptime_pct: number;
  version: string;
  details?: string;
}

export interface SystemHealthMetrics {
  overall_status: 'HEALTHY' | 'DEGRADED' | 'DOWN';
  uptime_seconds: number;
  cpu_usage_pct: number;
  memory_usage_pct: number;
  disk_usage_pct: number;
  network_in_kbps: number;
  network_out_kbps: number;
  services: ServiceStatusItem[];
  last_checked: string;
}

export interface ApiEndpointMetric {
  endpoint: string;
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  total_requests: number;
  success_count: number;
  error_count: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  status_2xx: number;
  status_4xx: number;
  status_5xx: number;
}

export interface ApiMetricsSummary {
  total_requests_24h: number;
  successful_requests: number;
  failed_requests: number;
  avg_response_time_ms: number;
  error_rate_pct: number;
  slowest_endpoints: ApiEndpointMetric[];
  most_frequent_endpoints: ApiEndpointMetric[];
}

export type LogSeverityLevel = 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL';

export interface ApplicationLogRecord {
  id: string;
  timestamp: string;
  level: LogSeverityLevel;
  service: string;
  module: string;
  message: string;
  stack_trace?: string;
  user_email?: string;
  ip_address?: string;
  metadata?: Record<string, any>;
}

export type NotificationCategory = 'SYSTEM' | 'SECURITY' | 'PREDICTION' | 'INVESTIGATION';

export interface NotificationItem {
  id: string;
  timestamp: string;
  title: string;
  message: string;
  category: NotificationCategory;
  severity: 'info' | 'warning' | 'error' | 'success';
  is_read: boolean;
  is_archived: boolean;
  action_url?: string;
}

export interface BackupRecord {
  id: string;
  timestamp: string;
  backup_name: string;
  size_gb: number;
  duration_seconds: number;
  type: 'AUTOMATED_DAILY' | 'MANUAL_SNAPSHOT' | 'POINT_IN_TIME';
  status: 'COMPLETED' | 'IN_PROGRESS' | 'FAILED';
  storage_location: string;
  checksum: string;
}

export interface BackupStatusOverview {
  last_backup_time: string;
  status: 'HEALTHY' | 'WARNING' | 'FAILED';
  storage_used_gb: number;
  total_storage_allocated_gb: number;
  recovery_readiness_pct: number;
  rpo_minutes: number;
  rto_minutes: number;
  backups: BackupRecord[];
}

export interface SystemConfigDetails {
  app_name: string;
  environment: 'production' | 'staging' | 'development';
  app_version: string;
  api_version: string;
  frontend_version: string;
  backend_version: string;
  database_version: string;
  ai_model_version: string;
  pytorch_version: string;
  build_hash: string;
  deployed_at: string;
  deployment_region: string;
  feature_flags: Record<string, boolean>;
}

export interface ObservabilityTimeSeriesPoint {
  timestamp: string;
  cpu_usage: number;
  memory_usage: number;
  qps: number;
  latency_ms: number;
  active_users: number;
  error_count: number;
}

export interface ObservabilityMetrics {
  current_qps: number;
  avg_p99_latency_ms: number;
  throughput_rpm: number;
  active_user_connections: number;
  history: ObservabilityTimeSeriesPoint[];
}

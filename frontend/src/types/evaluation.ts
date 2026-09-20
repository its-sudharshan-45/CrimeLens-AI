/**
 * TypeScript definitions for Phase 8.2 – Deep Learning Model Evaluation & MLOps
 */

export interface EvaluationMetrics {
  model_name: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  roc_auc: number;
  pr_auc: number;
  cohen_kappa: number;
  mcc: number;
  inference_latency_ms: number;
  validation_accuracy: number;
  validation_loss: number;
  training_accuracy: number;
  training_loss: number;
}

export interface ClassMetric {
  domain_name: string;
  precision: number;
  recall: number;
  f1_score: number;
  support: number;
}

export interface ConfusionMatrixData {
  labels: string[];
  matrix: number[][];
  per_class_metrics: ClassMetric[];
}

export interface TrainingEpochMetric {
  epoch: number;
  train_loss: number;
  val_loss: number;
  train_acc: number;
  val_acc: number;
  learning_rate: number;
}

export interface ModelBenchmarkComparison {
  model_name: string;
  architecture: string;
  version: string;
  accuracy: number;
  f1_score: number;
  mean_latency_ms: number;
  throughput_qps: number;
  peak_memory_mb: number;
  model_size_mb: number;
  parameters_count: number;
  dataset_version: string;
  training_date: string;
  is_best?: boolean;
}

export interface DatasetMetadata {
  dataset_name: string;
  dataset_version: string;
  total_rows: number;
  feature_count: number;
  train_samples: number;
  val_samples: number;
  test_samples: number;
  missing_values_pct: number;
  target_classes_count: number;
  class_distribution: Record<string, number>;
  last_updated: string;
}

export interface HyperparameterConfig {
  optimizer: string;
  loss_function: string;
  learning_rate: number;
  lr_scheduler: string;
  batch_size: number;
  epochs: number;
  dropout: number;
  embedding_dim: number;
  hidden_layers: number[];
  activation: string;
  weight_decay: number;
  early_stopping_patience: number;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  user_email: string;
  model_name: string;
  model_version: string;
  predicted_domain: string;
  confidence_score: number;
  execution_time_ms: number;
  xai_generated: boolean;
  city: string;
}

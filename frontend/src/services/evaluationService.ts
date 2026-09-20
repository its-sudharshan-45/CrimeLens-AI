import {
  EvaluationMetrics,
  ConfusionMatrixData,
  TrainingEpochMetric,
  ModelBenchmarkComparison,
  DatasetMetadata,
  HyperparameterConfig,
  AuditLogEntry,
} from '@/types/evaluation';

export const evaluationService = {
  getEvaluationMetrics(): EvaluationMetrics {
    return {
      model_name: 'FTTransformerClassifier',
      accuracy: 0.942,
      precision: 0.938,
      recall: 0.942,
      f1_score: 0.94,
      roc_auc: 0.985,
      pr_auc: 0.978,
      cohen_kappa: 0.912,
      mcc: 0.915,
      inference_latency_ms: 1.24,
      validation_accuracy: 0.938,
      validation_loss: 0.184,
      training_accuracy: 0.965,
      training_loss: 0.112,
    };
  },

  getConfusionMatrix(): ConfusionMatrixData {
    return {
      labels: ['Theft', 'Assault', 'Burglary', 'Robbery', 'Cybercrime', 'Homicide'],
      matrix: [
        [340, 12, 15, 8, 4, 1],
        [10, 290, 8, 14, 2, 6],
        [18, 9, 310, 12, 1, 0],
        [6, 15, 10, 265, 0, 4],
        [3, 1, 2, 1, 380, 0],
        [0, 4, 1, 3, 0, 192],
      ],
      per_class_metrics: [
        { domain_name: 'Theft', precision: 0.902, recall: 0.895, f1_score: 0.898, support: 380 },
        { domain_name: 'Assault', precision: 0.876, recall: 0.879, f1_score: 0.877, support: 330 },
        { domain_name: 'Burglary', precision: 0.896, recall: 0.886, f1_score: 0.891, support: 350 },
        { domain_name: 'Robbery', precision: 0.875, recall: 0.883, f1_score: 0.879, support: 300 },
        { domain_name: 'Cybercrime', precision: 0.977, recall: 0.982, f1_score: 0.979, support: 387 },
        { domain_name: 'Homicide', precision: 0.928, recall: 0.96, f1_score: 0.944, support: 200 },
      ],
    };
  },

  getTrainingHistory(): TrainingEpochMetric[] {
    const history: TrainingEpochMetric[] = [];
    let lr = 0.001;

    for (let i = 1; i <= 30; i++) {
      // Simulate realistic loss decay & accuracy rise with early stopping best at epoch 24
      const trainLoss = Math.max(0.08, 0.85 * Math.exp(-0.12 * i) + (Math.random() * 0.02 - 0.01));
      const valLoss = Math.max(0.18, 0.9 * Math.exp(-0.1 * i) + (i > 24 ? 0.005 * (i - 24) : 0) + (Math.random() * 0.02 - 0.01));
      const trainAcc = Math.min(0.97, 0.55 + 0.42 * (1 - Math.exp(-0.12 * i)));
      const valAcc = Math.min(0.942, 0.52 + 0.42 * (1 - Math.exp(-0.1 * i)) - (i > 24 ? 0.002 * (i - 24) : 0));
      lr = 0.001 * 0.5 * (1 + Math.cos((Math.PI * i) / 30));

      history.push({
        epoch: i,
        train_loss: Number(trainLoss.toFixed(4)),
        val_loss: Number(valLoss.toFixed(4)),
        train_acc: Number(trainAcc.toFixed(4)),
        val_acc: Number(valAcc.toFixed(4)),
        learning_rate: Number(lr.toFixed(6)),
      });
    }

    return history;
  },

  getBenchmarks(): ModelBenchmarkComparison[] {
    return [
      {
        model_name: 'FTTransformerClassifier',
        architecture: 'Feature Tokenizer Transformer',
        version: 'v1.0.0',
        accuracy: 0.942,
        f1_score: 0.94,
        mean_latency_ms: 1.24,
        throughput_qps: 806.4,
        peak_memory_mb: 48.2,
        model_size_mb: 18.4,
        parameters_count: 1420500,
        dataset_version: 'v2.1',
        training_date: '2026-07-28',
        is_best: true,
      },
      {
        model_name: 'EnsembleClassifier',
        architecture: 'Weighted Soft-Voting Ensemble',
        version: 'v1.0.0',
        accuracy: 0.948,
        f1_score: 0.946,
        mean_latency_ms: 3.82,
        throughput_qps: 261.7,
        peak_memory_mb: 84.6,
        model_size_mb: 32.8,
        parameters_count: 2841000,
        dataset_version: 'v2.1',
        training_date: '2026-07-28',
      },
      {
        model_name: 'ResidualMLPClassifier',
        architecture: 'Deep Residual MLP',
        version: 'v0.9.2',
        accuracy: 0.915,
        f1_score: 0.912,
        mean_latency_ms: 0.48,
        throughput_qps: 2083.3,
        peak_memory_mb: 22.1,
        model_size_mb: 6.2,
        parameters_count: 420800,
        dataset_version: 'v2.0',
        training_date: '2026-07-20',
      },
      {
        model_name: 'CatBoostBaseline',
        architecture: 'Gradient Boosted Decision Trees',
        version: 'v0.8.0',
        accuracy: 0.892,
        f1_score: 0.888,
        mean_latency_ms: 0.85,
        throughput_qps: 1176.4,
        peak_memory_mb: 34.0,
        model_size_mb: 12.1,
        parameters_count: 150000,
        dataset_version: 'v1.5',
        training_date: '2026-07-10',
      },
    ];
  },

  getDatasetInfo(): DatasetMetadata {
    return {
      dataset_name: 'CrimeLens-India-Primary-Dataset',
      dataset_version: 'v2.1',
      total_rows: 40160,
      feature_count: 18,
      train_samples: 28112,
      val_samples: 6024,
      test_samples: 6024,
      missing_values_pct: 0.0,
      target_classes_count: 6,
      class_distribution: {
        Theft: 12450,
        Assault: 9820,
        Burglary: 7640,
        Robbery: 5120,
        Cybercrime: 3410,
        Homicide: 1720,
      },
      last_updated: '2026-07-28 14:30:00 UTC',
    };
  },

  getHyperparameters(): HyperparameterConfig {
    return {
      optimizer: 'AdamW',
      loss_function: 'CrossEntropyLoss (label_smoothing=0.05)',
      learning_rate: 0.001,
      lr_scheduler: 'CosineAnnealingLR (T_max=30)',
      batch_size: 64,
      epochs: 30,
      dropout: 0.2,
      embedding_dim: 64,
      hidden_layers: [256, 128, 64],
      activation: 'GELU',
      weight_decay: 0.01,
      early_stopping_patience: 6,
    };
  },

  getAuditLogs(): AuditLogEntry[] {
    return [
      {
        id: 'pred-7f8a9b2c',
        timestamp: '2026-08-03 10:42:15',
        user_email: 'investigator@crimelens.ai',
        model_name: 'FTTransformerClassifier',
        model_version: 'v1.0.0',
        predicted_domain: 'Theft',
        confidence_score: 0.9482,
        execution_time_ms: 1,
        xai_generated: true,
        city: 'Mumbai',
      },
      {
        id: 'pred-3e4d5c6b',
        timestamp: '2026-08-03 10:35:40',
        user_email: 'officer@crimelens.ai',
        model_name: 'FTTransformerClassifier',
        model_version: 'v1.0.0',
        predicted_domain: 'Cybercrime',
        confidence_score: 0.9891,
        execution_time_ms: 2,
        xai_generated: true,
        city: 'Bangalore',
      },
      {
        id: 'pred-1a2b3c4d',
        timestamp: '2026-08-03 09:58:12',
        user_email: 'analyst@crimelens.ai',
        model_name: 'NBEATSForecaster',
        model_version: 'v1.0.0',
        predicted_domain: 'Trend Forecast (30d)',
        confidence_score: 0.912,
        execution_time_ms: 4,
        xai_generated: false,
        city: 'Delhi',
      },
      {
        id: 'pred-9f8e7d6c',
        timestamp: '2026-08-03 09:12:05',
        user_email: 'admin@crimelens.ai',
        model_name: 'EnsembleClassifier',
        model_version: 'v1.0.0',
        predicted_domain: 'Burglary',
        confidence_score: 0.8754,
        execution_time_ms: 3,
        xai_generated: true,
        city: 'Hyderabad',
      },
    ];
  },
};

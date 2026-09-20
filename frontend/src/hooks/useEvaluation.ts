import { useQuery } from '@tanstack/react-query';
import { evaluationService } from '@/services/evaluationService';

export const EVAL_KEYS = {
  metrics: ['eval', 'metrics'] as const,
  matrix: ['eval', 'matrix'] as const,
  history: ['eval', 'history'] as const,
  benchmarks: ['eval', 'benchmarks'] as const,
  dataset: ['eval', 'dataset'] as const,
  hyperparams: ['eval', 'hyperparams'] as const,
  auditLogs: ['eval', 'auditLogs'] as const,
};

export function useEvaluationMetrics() {
  return useQuery({
    queryKey: EVAL_KEYS.metrics,
    queryFn: () => evaluationService.getEvaluationMetrics(),
    staleTime: 5 * 60_000,
  });
}

export function useConfusionMatrix() {
  return useQuery({
    queryKey: EVAL_KEYS.matrix,
    queryFn: () => evaluationService.getConfusionMatrix(),
    staleTime: 5 * 60_000,
  });
}

export function useTrainingHistory() {
  return useQuery({
    queryKey: EVAL_KEYS.history,
    queryFn: () => evaluationService.getTrainingHistory(),
    staleTime: 5 * 60_000,
  });
}

export function useBenchmarks() {
  return useQuery({
    queryKey: EVAL_KEYS.benchmarks,
    queryFn: () => evaluationService.getBenchmarks(),
    staleTime: 5 * 60_000,
  });
}

export function useDatasetInfo() {
  return useQuery({
    queryKey: EVAL_KEYS.dataset,
    queryFn: () => evaluationService.getDatasetInfo(),
    staleTime: 5 * 60_000,
  });
}

export function useHyperparameters() {
  return useQuery({
    queryKey: EVAL_KEYS.hyperparams,
    queryFn: () => evaluationService.getHyperparameters(),
    staleTime: 5 * 60_000,
  });
}

export function useAuditLogs() {
  return useQuery({
    queryKey: EVAL_KEYS.auditLogs,
    queryFn: () => evaluationService.getAuditLogs(),
    staleTime: 30_000,
  });
}

import { useQuery } from '@tanstack/react-query';
import { mlopsService } from '@/services/mlopsService';

export const MLOPS_KEYS = {
  models: ['mlops', 'models'] as const,
  currentModel: ['mlops', 'models', 'current'] as const,
  analytics: ['mlops', 'analytics'] as const,
  driftStatus: ['mlops', 'drift'] as const,
  driftReport: ['mlops', 'drift', 'report'] as const,
  systemStatus: ['mlops', 'system'] as const,
};

/** All registered model versions */
export function useMLOpsModels() {
  return useQuery({
    queryKey: MLOPS_KEYS.models,
    queryFn: () => mlopsService.listModels(),
    staleTime: 5 * 60_000,
  });
}

/** Currently active model */
export function useCurrentModel() {
  return useQuery({
    queryKey: MLOPS_KEYS.currentModel,
    queryFn: () => mlopsService.getCurrentModel(),
    staleTime: 5 * 60_000,
  });
}

/** Prediction analytics dashboard – refreshed every 60s */
export function useAnalytics() {
  return useQuery({
    queryKey: MLOPS_KEYS.analytics,
    queryFn: () => mlopsService.getAnalytics(),
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
}

/** Live drift monitoring status – refreshed every 30s */
export function useDriftStatus() {
  return useQuery({
    queryKey: MLOPS_KEYS.driftStatus,
    queryFn: () => mlopsService.getDriftStatus(),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}

/** Detailed drift report – refreshed every 2 minutes */
export function useDriftReport() {
  return useQuery({
    queryKey: MLOPS_KEYS.driftReport,
    queryFn: () => mlopsService.getDriftReport(),
    staleTime: 2 * 60_000,
  });
}

/** Production system status – refreshed every 30s */
export function useSystemStatus() {
  return useQuery({
    queryKey: MLOPS_KEYS.systemStatus,
    queryFn: () => mlopsService.getSystemStatus(),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}

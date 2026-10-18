import { useQuery } from '@tanstack/react-query';
import { predictionService } from '@/services/predictionService';

export const PREDICTION_KEYS = {
  history: (page: number, pageSize: number, type?: string) =>
    ['predictions', 'history', page, pageSize, type] as const,
  stats: ['predictions', 'stats'] as const,
};

/** Prediction history query */
export function usePredictionHistory(page = 1, pageSize = 20, predictionType?: string) {
  return useQuery({
    queryKey: PREDICTION_KEYS.history(page, pageSize, predictionType),
    queryFn: () => predictionService.getPredictionHistory(page, pageSize, predictionType),
    staleTime: 30_000,
    retry: 1,
  });
}

/** Aggregate prediction observability metrics */
export function usePredictionStats() {
  return useQuery({
    queryKey: PREDICTION_KEYS.stats,
    queryFn: () => predictionService.getPredictionStats(),
    staleTime: 30_000,
    refetchInterval: 30_000,
    retry: 1,
  });
}

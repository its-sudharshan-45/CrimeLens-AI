import { useQuery, useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { aiService } from '@/services/aiService';
import type {
  CrimePredictionRequest,
  ForecastRequest,
  ExplainabilityRequest,
} from '@/types/ai';

export const AI_KEYS = {
  health: ['ai', 'health'] as const,
  metadata: ['ai', 'metadata'] as const,
};

/** Live model health – auto-refetches every 30s */
export function useAIHealth() {
  return useQuery({
    queryKey: AI_KEYS.health,
    queryFn: () => aiService.getHealthStatus(),
    staleTime: 30_000,
    refetchInterval: 30_000,
    retry: 1,
  });
}

/** Model version metadata – cached for 5 minutes */
export function useModelMetadata() {
  return useQuery({
    queryKey: AI_KEYS.metadata,
    queryFn: () => aiService.getModelMetadata(),
    staleTime: 5 * 60_000,
    retry: 1,
  });
}

/** Real-time crime domain prediction mutation */
export function usePrediction() {
  return useMutation({
    mutationFn: (payload: CrimePredictionRequest) => aiService.predict(payload),
    onError: (e: Error) => toast.error(`Prediction failed: ${e.message}`),
  });
}

/** N-BEATS crime trend forecast mutation */
export function useForecast() {
  return useMutation({
    mutationFn: (payload: ForecastRequest) => aiService.forecast(payload),
    onError: (e: Error) => toast.error(`Forecast failed: ${e.message}`),
  });
}

/** Captum XAI explainability mutation */
export function useExplainability() {
  return useMutation({
    mutationFn: (payload: ExplainabilityRequest) => aiService.explain(payload),
    onError: (e: Error) => toast.error(`XAI analysis failed: ${e.message}`),
  });
}

/** Batch prediction mutation */
export function useBatchPredict() {
  return useMutation({
    mutationFn: (records: CrimePredictionRequest[]) => aiService.batchPredict(records),
    onSuccess: (data) => toast.success(`Batch complete: ${data.total_records} records processed`),
    onError: (e: Error) => toast.error(`Batch prediction failed: ${e.message}`),
  });
}

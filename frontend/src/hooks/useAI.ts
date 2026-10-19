import { useMutation, useQuery } from '@tanstack/react-query';
import { aiService } from '@/services/aiService';
import type { RiskPredictionRequest } from '@/types/ai';

export const AI_KEYS = {
  health: ['ai', 'health'] as const,
  locations: ['ai', 'locations'] as const,
};

/** Model availability. Auto-refreshes every 60 seconds. */
export function useAIHealth() {
  return useQuery({
    queryKey: AI_KEYS.health,
    queryFn: () => aiService.getHealth(),
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: 1,
  });
}

/** State/district catalog. Cached for ten minutes because it is static. */
export function useLocations() {
  return useQuery({
    queryKey: AI_KEYS.locations,
    queryFn: () => aiService.getLocations(),
    staleTime: 10 * 60_000,
    retry: 1,
  });
}

/**
 * Runs a prediction only when the user submits the form. This keeps the page
 * deterministic: selecting a dropdown does not silently fire model requests.
 */
export function useRiskPrediction() {
  return useMutation({
    mutationKey: ['ai', 'risk'],
    mutationFn: (payload: RiskPredictionRequest) => aiService.predictRisk(payload),
  });
}

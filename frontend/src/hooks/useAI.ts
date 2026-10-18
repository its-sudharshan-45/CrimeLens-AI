import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { aiService } from '@/services/aiService';
import type { ForecastRequest, ScopeType } from '@/types/ai';

export const AI_KEYS = {
  health: ['ai', 'health'] as const,
  metadata: ['ai', 'metadata'] as const,
  scopes: (scopeType?: ScopeType) => ['ai', 'scopes', scopeType ?? 'all'] as const,
  forecast: (scopeKey?: string) => ['ai', 'forecast', scopeKey ?? 'none'] as const,
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

/** Active model metadata – cached for 5 minutes */
export function useModelMetadata() {
  return useQuery({
    queryKey: AI_KEYS.metadata,
    queryFn: () => aiService.getModelMetadata(),
    staleTime: 5 * 60_000,
    retry: 1,
  });
}

/** Every selectable forecasting scope, optionally filtered by type. */
export function useScopes(scopeType?: ScopeType) {
  return useQuery({
    queryKey: AI_KEYS.scopes(scopeType),
    queryFn: () => aiService.getScopes(scopeType),
    staleTime: 10 * 60_000,
    retry: 1,
  });
}

/**
 * Runs a genuine GRU forecast for the selected scope.
 * Disabled until a scope type + value are chosen.
 */
export function useForecast(params: ForecastRequest | null) {
  const key = params ? `${params.scope_type}:${params.scope_value}` : undefined;
  return useQuery({
    queryKey: AI_KEYS.forecast(key),
    queryFn: () => aiService.forecast(params as ForecastRequest),
    enabled: Boolean(params?.scope_type && params?.scope_value),
    staleTime: 5 * 60_000,
    retry: 1,
    throwOnError: (error) => {
      toast.error(`Forecast failed: ${(error as Error).message}`);
      return false;
    },
  });
}

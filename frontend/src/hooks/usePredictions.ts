import { useQuery, useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { predictionService } from '@/services/predictionService';
import type {
  HotspotPredictionRequest,
  TemporalRiskRequest,
  InvestigationLeadRequest,
} from '@/types/prediction';

export const PREDICTION_KEYS = {
  hotspots: (params?: HotspotPredictionRequest) => ['predictions', 'hotspots', params] as const,
  temporalRisk: (city: string) => ['predictions', 'temporalRisk', city] as const,
  investigationLeads: (city: string, crimeType?: string) => ['predictions', 'investigationLeads', city, crimeType] as const,
  history: (page: number, pageSize: number, type?: string) => ['predictions', 'history', page, pageSize, type] as const,
};

/** Hotspot prediction query */
export function useHotspots(params?: HotspotPredictionRequest) {
  return useQuery({
    queryKey: PREDICTION_KEYS.hotspots(params),
    queryFn: () => predictionService.getHotspots(params),
    staleTime: 60_000,
    retry: 1,
  });
}

/** Hotspot prediction mutation (for manual refetch/filtering) */
export function useHotspotsMutation() {
  return useMutation({
    mutationFn: (params?: HotspotPredictionRequest) => predictionService.getHotspots(params),
    onError: (e: Error) => toast.error(`Hotspot prediction failed: ${e.message}`),
  });
}

/** Temporal crime forecasting mutation */
export function useTemporalRiskMutation() {
  return useMutation({
    mutationFn: (params: TemporalRiskRequest) => predictionService.getTemporalRisk(params),
    onError: (e: Error) => toast.error(`Temporal risk forecast failed: ${e.message}`),
  });
}

/** Temporal crime forecasting query */
export function useTemporalRisk(city: string) {
  return useQuery({
    queryKey: PREDICTION_KEYS.temporalRisk(city),
    queryFn: () => predictionService.getTemporalRisk({ city }),
    enabled: Boolean(city),
    staleTime: 60_000,
    retry: 1,
  });
}

/** Investigation priorities mutation */
export function useInvestigationLeadsMutation() {
  return useMutation({
    mutationFn: (params: InvestigationLeadRequest) => predictionService.getInvestigationLeads(params),
    onError: (e: Error) => toast.error(`Investigation leads generation failed: ${e.message}`),
  });
}

/** Investigation priorities query */
export function useInvestigationLeads(city: string, crimeType?: string) {
  return useQuery({
    queryKey: PREDICTION_KEYS.investigationLeads(city, crimeType),
    queryFn: () => predictionService.getInvestigationLeads({ city, crime_type: crimeType }),
    enabled: Boolean(city),
    staleTime: 60_000,
    retry: 1,
  });
}

/** Prediction history query */
export function usePredictionHistory(page = 1, pageSize = 20, predictionType?: string) {
  return useQuery({
    queryKey: PREDICTION_KEYS.history(page, pageSize, predictionType),
    queryFn: () => predictionService.getPredictionHistory(page, pageSize, predictionType),
    staleTime: 30_000,
    retry: 1,
  });
}

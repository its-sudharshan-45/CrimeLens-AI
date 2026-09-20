import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { crimeLocationService } from '@/services/crimeLocationService';
import type { CrimeLocationCreate, CrimeLocationUpdate, CrimeLocationFilters } from '@/types/crimeLocation';
import { useAuth } from '@/hooks/useAuth';

export const CRIME_LOCATIONS_KEY = 'crime-locations';

export function useCrimeLocations(filters: CrimeLocationFilters = {}) {
  const { isAuthenticated, loading } = useAuth();
  return useQuery({
    queryKey: [CRIME_LOCATIONS_KEY, filters],
    queryFn: () => crimeLocationService.list(filters),
    enabled: !loading && isAuthenticated,
    staleTime: 60_000,
  });
}

export function useCrimeLocation(id: string | null) {
  return useQuery({
    queryKey: [CRIME_LOCATIONS_KEY, id],
    queryFn: () => crimeLocationService.getById(id!),
    enabled: !!id,
  });
}

export function useCreateCrimeLocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CrimeLocationCreate) => crimeLocationService.create(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [CRIME_LOCATIONS_KEY] });
      toast.success('Location created successfully.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useUpdateCrimeLocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: CrimeLocationUpdate }) =>
      crimeLocationService.update(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [CRIME_LOCATIONS_KEY] });
      toast.success('Location updated.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useDeleteCrimeLocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => crimeLocationService.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [CRIME_LOCATIONS_KEY] });
      toast.success('Location deleted.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

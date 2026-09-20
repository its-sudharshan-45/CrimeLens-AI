import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { crimeCategoryService } from '@/services/crimeCategoryService';
import type { CrimeCategoryCreate, CrimeCategoryUpdate, CrimeCategoryFilters } from '@/types/crimeCategory';
import { useAuth } from '@/hooks/useAuth';

export const CRIME_CATEGORIES_KEY = 'crime-categories';

export function useCrimeCategories(filters: CrimeCategoryFilters = {}) {
  const { isAuthenticated, loading } = useAuth();
  return useQuery({
    queryKey: [CRIME_CATEGORIES_KEY, filters],
    queryFn: () => crimeCategoryService.list(filters),
    enabled: !loading && isAuthenticated,
    staleTime: 60_000,
  });
}

export function useCrimeCategory(id: string | null) {
  return useQuery({
    queryKey: [CRIME_CATEGORIES_KEY, id],
    queryFn: () => crimeCategoryService.getById(id!),
    enabled: !!id,
  });
}

export function useCreateCrimeCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CrimeCategoryCreate) => crimeCategoryService.create(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [CRIME_CATEGORIES_KEY] });
      toast.success('Category created successfully.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useUpdateCrimeCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: CrimeCategoryUpdate }) =>
      crimeCategoryService.update(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [CRIME_CATEGORIES_KEY] });
      toast.success('Category updated.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useDeleteCrimeCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => crimeCategoryService.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [CRIME_CATEGORIES_KEY] });
      toast.success('Category deleted.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

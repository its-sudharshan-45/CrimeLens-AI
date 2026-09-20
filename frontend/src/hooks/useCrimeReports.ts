import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { crimeReportService } from '@/services/crimeReportService';
import type { CrimeReportCreate, CrimeReportUpdate, CrimeReportFilters } from '@/types/crimeReport';
import { useAuth } from '@/hooks/useAuth';

export const CRIME_REPORTS_KEY = 'crime-reports';

export function useCrimeReports(filters: CrimeReportFilters = {}) {
  const { isAuthenticated, loading } = useAuth();
  return useQuery({
    queryKey: [CRIME_REPORTS_KEY, filters],
    queryFn: () => crimeReportService.list(filters),
    enabled: !loading && isAuthenticated,
    staleTime: 30_000,
    retry: (count, error) => count < 2 && (error as Error & { status?: number }).status !== 401,
  });
}

export function useCrimeReport(id: string | null) {
  const { isAuthenticated, loading } = useAuth();
  return useQuery({
    queryKey: [CRIME_REPORTS_KEY, id],
    queryFn: () => crimeReportService.getById(id!),
    enabled: !loading && isAuthenticated && !!id,
    staleTime: 60_000,
  });
}

export function useCreateCrimeReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CrimeReportCreate) => crimeReportService.create(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [CRIME_REPORTS_KEY] });
      toast.success('Crime report created successfully.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useUpdateCrimeReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: CrimeReportUpdate }) =>
      crimeReportService.update(id, payload),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: [CRIME_REPORTS_KEY] });
      qc.setQueryData([CRIME_REPORTS_KEY, data.id], data);
      toast.success('Crime report updated.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useDeleteCrimeReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => crimeReportService.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [CRIME_REPORTS_KEY] });
      toast.success('Crime report deleted.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

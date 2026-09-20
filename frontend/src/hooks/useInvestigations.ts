import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { investigationService } from '@/services/investigationService';
import type {
  InvestigationCreate,
  InvestigationStatusUpdate,
  InvestigationAssign,
  InvestigationNoteCreate,
  InvestigationNoteUpdate,
  InvestigationFilters,
} from '@/types/investigation';
import { useAuth } from '@/hooks/useAuth';

export const INVESTIGATIONS_KEY = 'investigations';

export function useInvestigations(filters: InvestigationFilters = {}) {
  const { isAuthenticated, loading } = useAuth();
  return useQuery({
    queryKey: [INVESTIGATIONS_KEY, filters],
    queryFn: () => investigationService.list(filters),
    enabled: !loading && isAuthenticated,
    staleTime: 30_000,
  });
}

export function useInvestigation(id: string | null) {
  return useQuery({
    queryKey: [INVESTIGATIONS_KEY, id],
    queryFn: () => investigationService.getById(id!),
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useInvestigationTimeline(id: string | null) {
  return useQuery({
    queryKey: [INVESTIGATIONS_KEY, id, 'timeline'],
    queryFn: () => investigationService.getTimeline(id!),
    enabled: !!id,
  });
}

export function useInvestigationNotes(id: string | null, page = 1) {
  return useQuery({
    queryKey: [INVESTIGATIONS_KEY, id, 'notes', page],
    queryFn: () => investigationService.getNotes(id!, page),
    enabled: !!id,
  });
}

export function useCreateInvestigation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: InvestigationCreate) => investigationService.create(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [INVESTIGATIONS_KEY] });
      toast.success('Investigation created successfully.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useUpdateInvestigationStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: InvestigationStatusUpdate }) =>
      investigationService.updateStatus(id, payload),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: [INVESTIGATIONS_KEY] });
      qc.setQueryData([INVESTIGATIONS_KEY, data.id], data);
      toast.success('Status updated.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useAssignInvestigator() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: InvestigationAssign }) =>
      investigationService.assign(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [INVESTIGATIONS_KEY] });
      toast.success('Investigator assigned.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useAddInvestigationNote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: InvestigationNoteCreate }) =>
      investigationService.addNote(id, payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: [INVESTIGATIONS_KEY, vars.id, 'notes'] });
      toast.success('Note added.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useUpdateInvestigationNote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ noteId, payload }: { noteId: string; payload: InvestigationNoteUpdate }) =>
      investigationService.updateNote(noteId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [INVESTIGATIONS_KEY] });
      toast.success('Note updated.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

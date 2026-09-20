import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { evidenceService } from '@/services/evidenceService';
import type { EvidenceUpdate } from '@/types/evidence';

export { evidenceService };
export const EVIDENCE_KEY = 'evidence';

export function useReportEvidence(reportId: string | null, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: [EVIDENCE_KEY, 'by-report', reportId, page, pageSize],
    queryFn: () => evidenceService.getByReport(reportId!, page, pageSize),
    enabled: !!reportId,
    staleTime: 30_000,
  });
}

export function useEvidence(id: string | null) {
  return useQuery({
    queryKey: [EVIDENCE_KEY, id],
    queryFn: () => evidenceService.getById(id!),
    enabled: !!id,
  });
}

export function useUploadEvidence() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      reportId,
      file,
      description,
      onProgress,
    }: {
      reportId: string;
      file: File;
      description?: string;
      onProgress?: (pct: number) => void;
    }) => evidenceService.upload(reportId, file, description, onProgress),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: [EVIDENCE_KEY, 'by-report', vars.reportId] });
      toast.success('Evidence uploaded successfully.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useUpdateEvidence() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: EvidenceUpdate }) =>
      evidenceService.update(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [EVIDENCE_KEY] });
      toast.success('Evidence updated.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useDeleteEvidence() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => evidenceService.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [EVIDENCE_KEY] });
      toast.success('Evidence deleted.');
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

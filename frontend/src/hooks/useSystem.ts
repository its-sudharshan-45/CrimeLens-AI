import { useQuery } from '@tanstack/react-query';
import { systemService } from '@/services/systemService';
import { AuditFilterParams } from '@/types/system';

export function useAuditCenter(params?: AuditFilterParams) {
  return useQuery({
    queryKey: ['audit-logs', params],
    queryFn: () => systemService.getAuditLogs(params),
    staleTime: 60 * 1000,
  });
}

export function useSecurityDashboard() {
  return useQuery({
    queryKey: ['security-overview'],
    queryFn: () => systemService.getSecurityOverview(),
    refetchInterval: 15 * 1000,
  });
}

export function useSystemHealth(options: { live?: boolean } = {}) {
  return useQuery({
    queryKey: ['system-health'],
    queryFn: () => systemService.getSystemHealth(),
    staleTime: options.live === false ? 30 * 1000 : 0,
    refetchInterval: options.live === false ? false : 10 * 1000,
  });
}

export function useBackupRecovery() {
  return useQuery({
    queryKey: ['backup-recovery'],
    queryFn: () => systemService.getBackupStatus(),
    staleTime: 2 * 60 * 1000,
  });
}


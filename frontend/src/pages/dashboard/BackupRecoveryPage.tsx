import { Badge } from '@/components/ui/Badge';

import { useBackupRecovery } from '@/hooks/useSystem';
import { BackupStatusWidget } from '@/components/system/BackupStatusWidget';

export default function BackupRecoveryPage() {
  const { data } = useBackupRecovery();

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-foreground">Backup & Disaster Recovery Dashboard</h1>
            <Badge variant="emerald">100% Recovery Ready</Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Automated database snapshot monitoring, RPO/RTO SLAs, storage utilization, and checksum verifications
          </p>
        </div>
      </div>

      {data && <BackupStatusWidget data={data} />}
    </div>
  );
}

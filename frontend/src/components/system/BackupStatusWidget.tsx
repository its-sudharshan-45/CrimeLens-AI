import { BackupStatusOverview } from '@/types/system';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Database, ShieldCheck, HardDrive, Clock, CheckCircle } from 'lucide-react';

interface BackupStatusWidgetProps {
  data: BackupStatusOverview;
}

export function BackupStatusWidget({ data }: BackupStatusWidgetProps) {
  const pct = Math.round((data.storage_used_gb / data.total_storage_allocated_gb) * 100);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Last Verified Backup</span>
            <Database size={16} className="text-emerald-400" />
          </div>
          <p className="text-lg font-bold text-foreground font-mono">{data.last_backup_time}</p>
          <Badge variant="emerald">Auto RPO 6 Hours Verified</Badge>
        </Card>

        <Card className="p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Recovery Readiness</span>
            <ShieldCheck size={16} className="text-blue-400" />
          </div>
          <p className="text-2xl font-bold text-emerald-400 font-mono">{data.recovery_readiness_pct}%</p>
          <p className="text-[11px] text-muted-foreground">Target RTO: {data.rto_minutes} min · RPO: {data.rpo_minutes} min</p>
        </Card>

        <Card className="p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Storage Allocated</span>
            <HardDrive size={16} className="text-purple-400" />
          </div>
          <p className="text-lg font-bold text-foreground font-mono">
            {data.storage_used_gb} GB / {data.total_storage_allocated_gb} GB
          </p>
          <div className="h-2 bg-secondary rounded-full overflow-hidden">
            <div className="h-full bg-purple-500 rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
          </div>
        </Card>
      </div>

      {/* Snapshot History Table */}
      <Card className="overflow-hidden">
        <div className="p-4 border-b border-border flex justify-between items-center">
          <h3 className="text-sm font-bold text-foreground">Backup Snapshots & Disaster Recovery Points</h3>
          <Badge variant="emerald">{data.backups.length} Snapshots</Badge>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                {['Snapshot Name', 'Timestamp', 'Type', 'Size', 'Duration', 'Checksum', 'Status'].map((h) => (
                  <th key={h} className="text-left px-4 py-2.5 text-muted-foreground font-semibold uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.backups.map((b) => (
                <tr key={b.id} className="border-b border-border/50 hover:bg-secondary/20">
                  <td className="px-4 py-3 font-mono font-semibold text-foreground">{b.backup_name}</td>
                  <td className="px-4 py-3 font-mono text-muted-foreground">{b.timestamp}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-blue-500/10 text-blue-400 border border-blue-500/20">
                      {b.type}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-foreground">{b.size_gb} GB</td>
                  <td className="px-4 py-3 font-mono text-muted-foreground flex items-center gap-1">
                    <Clock size={12} /> {b.duration_seconds}s
                  </td>
                  <td className="px-4 py-3 font-mono text-muted-foreground truncate max-w-[120px]">{b.checksum}</td>
                  <td className="px-4 py-3">
                    <Badge variant="emerald" className="flex items-center gap-1 w-fit">
                      <CheckCircle size={10} /> {b.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

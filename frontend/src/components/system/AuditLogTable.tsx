import { useState } from 'react';
import { AuditLogRecord } from '@/types/system';
import { Badge } from '@/components/ui/Badge';
import { Info, Clock, Monitor, ShieldCheck, AlertOctagon } from 'lucide-react';

interface AuditLogTableProps {
  logs: AuditLogRecord[];
  isLoading?: boolean;
}

export function AuditLogTable({ logs, isLoading }: AuditLogTableProps) {
  const [selectedLog, setSelectedLog] = useState<AuditLogRecord | null>(null);

  const getStatusBadge = (status: AuditLogRecord['status']) => {
    switch (status) {
      case 'SUCCESS':
        return <Badge variant="emerald">Success</Badge>;
      case 'FAILURE':
        return <Badge variant="amber">Failure</Badge>;
      case 'DENIED':
        return <Badge variant="red">Denied</Badge>;
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  const getCategoryColor = (category: AuditLogRecord['category']) => {
    switch (category) {
      case 'AUTH': return 'text-purple-400 bg-purple-500/10 border-purple-500/20';
      case 'AI': return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      case 'EVIDENCE': return 'text-blue-400 bg-blue-500/10 border-blue-500/20';
      case 'INVESTIGATION': return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'ADMIN': return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
      default: return 'text-muted-foreground bg-secondary';
    }
  };

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-xl border border-border">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border bg-secondary/30">
              <th className="text-left px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider">Timestamp</th>
              <th className="text-left px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider">User</th>
              <th className="text-left px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider">Category</th>
              <th className="text-left px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider">Action</th>
              <th className="text-left px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider">IP / Browser</th>
              <th className="text-left px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider">Status</th>
              <th className="text-right px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider">Details</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-border/50">
                  <td colSpan={7} className="px-4 py-4">
                    <div className="h-4 bg-secondary/60 rounded animate-pulse w-full" />
                  </td>
                </tr>
              ))
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-muted-foreground">
                  No audit log entries found matching criteria.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="border-b border-border/50 hover:bg-secondary/20 transition-colors">
                  <td className="px-4 py-3 font-mono text-muted-foreground whitespace-nowrap">{log.timestamp}</td>
                  <td className="px-4 py-3">
                    <div className="font-semibold text-foreground">{log.user_email}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono border font-semibold ${getCategoryColor(log.category)}`}>
                      {log.category}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono font-medium text-foreground">{log.action}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    <div className="font-mono text-[11px]">{log.ip_address}</div>
                    <div className="text-[10px] text-muted-foreground/80 truncate max-w-[120px]">{log.browser} ({log.os})</div>
                  </td>
                  <td className="px-4 py-3">{getStatusBadge(log.status)}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => setSelectedLog(log)}
                      className="p-1 text-emerald-400 hover:bg-emerald-500/10 rounded transition-colors"
                      title="Inspect Log Details"
                    >
                      <Info size={16} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Log Detail Drawer Modal */}
      {selectedLog && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl animate-fade-in">
            <div className="flex justify-between items-center border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck size={18} className="text-emerald-400" />
                <h3 className="font-bold text-foreground text-sm">Audit Log Detail: {selectedLog.id}</h3>
              </div>
              <button onClick={() => setSelectedLog(null)} className="text-muted-foreground hover:text-foreground text-sm font-semibold">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between border-b border-border/40 pb-2">
                <span className="text-muted-foreground flex items-center gap-1"><Clock size={12} /> Timestamp</span>
                <span className="font-mono font-semibold text-foreground">{selectedLog.timestamp}</span>
              </div>
              <div className="flex justify-between border-b border-border/40 pb-2">
                <span className="text-muted-foreground">User</span>
                <span className="font-semibold text-foreground">{selectedLog.user_email}</span>
              </div>
              <div className="flex justify-between border-b border-border/40 pb-2">
                <span className="text-muted-foreground flex items-center gap-1"><Monitor size={12} /> Client Info</span>
                <span className="font-mono text-foreground">{selectedLog.ip_address} · {selectedLog.browser} ({selectedLog.os})</span>
              </div>
              <div className="flex justify-between border-b border-border/40 pb-2">
                <span className="text-muted-foreground flex items-center gap-1"><AlertOctagon size={12} /> Status & Time</span>
                <span className="font-semibold text-emerald-400">{selectedLog.status} ({selectedLog.execution_time_ms ?? 0} ms)</span>
              </div>

              {selectedLog.details && (
                <div className="space-y-1.5 pt-1">
                  <span className="text-muted-foreground font-semibold">Action Metadata Payload:</span>
                  <pre className="p-3 bg-secondary/80 rounded-xl text-foreground font-mono text-[11px] overflow-auto max-h-40">
                    {JSON.stringify(selectedLog.details, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-1.5 bg-secondary hover:bg-secondary/80 text-foreground font-semibold rounded-lg text-xs"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

import { useState } from 'react';
import { ShieldCheck, Download, Search, Filter } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { StatCard } from '@/components/ui/StatCard';

import { useAuditCenter } from '@/hooks/useSystem';
import { AuditLogTable } from '@/components/system/AuditLogTable';
import { AuditCategory, AuditStatus } from '@/types/system';
import { exportToCSV, exportToJSON } from '@/utils/exportUtils';
import { toast } from 'sonner';

export default function AuditCenterPage() {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<AuditCategory | 'ALL'>('ALL');
  const [status, setStatus] = useState<AuditStatus | 'ALL'>('ALL');

  const { data: logs = [], isLoading } = useAuditCenter({ search, category, status });

  const handleExportCSV = () => {
    if (!logs.length) return toast.error('No logs to export.');
    exportToCSV('enterprise_audit_log.csv', logs);
    toast.success('Audit logs exported to CSV');
  };

  const handleExportJSON = () => {
    if (!logs.length) return toast.error('No logs to export.');
    exportToJSON('enterprise_audit_log.json', logs);
    toast.success('Audit logs exported to JSON');
  };

  const successCount = logs.filter((l) => l.status === 'SUCCESS').length;
  const deniedCount = logs.filter((l) => l.status === 'DENIED' || l.status === 'FAILURE').length;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-foreground">Enterprise Audit Center</h1>
            <Badge variant="emerald">Cryptographic Audit Trail</Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Centralized immutable tracking of authentication, predictions, evidence ops, and administrative actions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExportCSV}>
            <Download size={14} className="mr-1.5" /> CSV
          </Button>
          <Button variant="outline" size="sm" onClick={handleExportJSON}>
            <Download size={14} className="mr-1.5" /> JSON
          </Button>
        </div>
      </div>

      {/* Stat Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Total Audit Events" value={logs.length} icon={<ShieldCheck size={18} />} accent="emerald" />
        <StatCard label="Successful Operations" value={successCount} icon={<ShieldCheck size={18} />} accent="blue" />
        <StatCard label="Denied / Failed" value={deniedCount} icon={<ShieldCheck size={18} />} accent="red" />
        <StatCard label="Categories Tracked" value={7} icon={<ShieldCheck size={18} />} accent="purple" />
      </div>

      {/* Filter Bar */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search size={14} className="absolute left-3 top-2.5 text-muted-foreground" />
            <Input
              placeholder="Search by action, user email, IP address, or ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-8 text-xs w-full"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Filter size={14} className="text-muted-foreground shrink-0" />
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as any)}
              className="h-8 px-2 bg-secondary border border-border rounded-md text-xs font-semibold text-foreground focus:outline-none"
            >
              <option value="ALL">All Categories</option>
              <option value="AUTH">Auth</option>
              <option value="AI">AI Serving</option>
              <option value="EVIDENCE">Evidence</option>
              <option value="INVESTIGATION">Investigation</option>
              <option value="ADMIN">System Admin</option>
            </select>

            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as any)}
              className="h-8 px-2 bg-secondary border border-border rounded-md text-xs font-semibold text-foreground focus:outline-none"
            >
              <option value="ALL">All Statuses</option>
              <option value="SUCCESS">Success</option>
              <option value="FAILURE">Failure</option>
              <option value="DENIED">Denied</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Table */}
      <AuditLogTable logs={logs} isLoading={isLoading} />
    </div>
  );
}

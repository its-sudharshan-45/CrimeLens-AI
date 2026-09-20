import { Activity, RefreshCw } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { StatCard } from '@/components/ui/StatCard';

import { useSystemHealth } from '@/hooks/useSystem';
import { HealthGaugeCard } from '@/components/system/HealthGaugeCard';

export default function SystemHealthPage() {
  const { data, refetch, isFetching } = useSystemHealth();

  const services = data?.services ?? [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-foreground">Live Infrastructure System Health</h1>
            <Badge variant="emerald" className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" /> Probe Active (10s)
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Real-time liveness & readiness monitoring across API services, PostgreSQL DB, PyTorch inference & MinIO
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} loading={isFetching}>
          <RefreshCw size={14} className="mr-1.5" /> Probe Now
        </Button>
      </div>

      {/* Primary Infrastructure Gauges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Overall Status" value={data?.overall_status ?? 'HEALTHY'} icon={<Activity size={18} />} accent="emerald" />
        <StatCard label="CPU Usage" value={`${data?.cpu_usage_pct ?? 0}%`} icon={<Activity size={18} />} accent="blue" />
        <StatCard label="Memory Usage" value={`${data?.memory_usage_pct ?? 0}%`} icon={<Activity size={18} />} accent="purple" />
        <StatCard label="Disk Usage" value={`${data?.disk_usage_pct ?? 0}%`} icon={<Activity size={18} />} accent="amber" />
      </div>

      {/* Network & Uptime Bar */}
      <Card className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4 text-xs font-mono">
          <div>System Uptime: <span className="text-emerald-400 font-bold">14d 10h 28m</span></div>
          <div>Network IN: <span className="text-foreground font-semibold">{data?.network_in_kbps} KB/s</span></div>
          <div>Network OUT: <span className="text-foreground font-semibold">{data?.network_out_kbps} KB/s</span></div>
        </div>
        <span className="text-[11px] text-muted-foreground font-mono">Last Checked: {data?.last_checked}</span>
      </Card>

      {/* Service Health Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {services.map((svc) => (
          <HealthGaugeCard key={svc.name} service={svc} />
        ))}
      </div>
    </div>
  );
}

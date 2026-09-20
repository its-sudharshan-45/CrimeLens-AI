import { ServiceStatusItem } from '@/types/system';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { CheckCircle2, AlertTriangle, XCircle, Activity, Clock } from 'lucide-react';

interface HealthGaugeCardProps {
  service: ServiceStatusItem;
}

export function HealthGaugeCard({ service }: HealthGaugeCardProps) {
  const getStatusIcon = () => {
    switch (service.status) {
      case 'HEALTHY':
        return <CheckCircle2 size={20} className="text-emerald-400" />;
      case 'DEGRADED':
        return <AlertTriangle size={20} className="text-amber-400" />;
      default:
        return <XCircle size={20} className="text-rose-400" />;
    }
  };

  const getStatusBadge = () => {
    switch (service.status) {
      case 'HEALTHY':
        return <Badge variant="emerald">Healthy</Badge>;
      case 'DEGRADED':
        return <Badge variant="amber">Degraded</Badge>;
      default:
        return <Badge variant="red">Down</Badge>;
    }
  };

  return (
    <Card className="p-5 space-y-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-secondary border border-border">
            {getStatusIcon()}
          </div>
          <div>
            <h4 className="text-xs font-bold text-foreground">{service.name}</h4>
            <span className="text-[10px] font-mono text-muted-foreground uppercase">{service.category} · {service.version}</span>
          </div>
        </div>
        {getStatusBadge()}
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs pt-2 border-t border-border/40">
        <div className="p-2.5 rounded-lg bg-secondary/30 border border-border/40">
          <span className="text-[10px] text-muted-foreground flex items-center gap-1 font-medium uppercase">
            <Clock size={10} /> Latency
          </span>
          <span className="font-mono font-bold text-foreground text-sm mt-0.5 block">{service.latency_ms} ms</span>
        </div>

        <div className="p-2.5 rounded-lg bg-secondary/30 border border-border/40">
          <span className="text-[10px] text-muted-foreground flex items-center gap-1 font-medium uppercase">
            <Activity size={10} /> Uptime
          </span>
          <span className="font-mono font-bold text-emerald-400 text-sm mt-0.5 block">{service.uptime_pct}%</span>
        </div>
      </div>
    </Card>
  );
}

import { cn } from '@/lib/utils';
import { Cpu, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import type { ModelHealthResponse } from '@/types/ai';

interface ModelHealthBadgeProps {
  health?: ModelHealthResponse;
  loading?: boolean;
  className?: string;
}

export function ModelHealthBadge({ health, loading, className }: ModelHealthBadgeProps) {
  if (loading) {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <div className="w-2 h-2 rounded-full bg-muted-foreground animate-pulse" />
        <span className="text-xs text-muted-foreground">Checking AI systems…</span>
      </div>
    );
  }

  if (!health) {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <XCircle size={13} className="text-red-400" />
        <span className="text-xs text-red-400">AI Subsystem Unavailable</span>
      </div>
    );
  }

  const isOk = health.status === 'ok' && health.loaded;
  const statusConfig = isOk
    ? {
        color: 'text-emerald-400',
        bg: 'bg-emerald-500/10 border-emerald-500/20',
        pulse: 'bg-emerald-500',
        Icon: CheckCircle2,
        label: 'Forecaster Online',
      }
    : {
        color: 'text-amber-400',
        bg: 'bg-amber-500/10 border-amber-500/20',
        pulse: 'bg-amber-500',
        Icon: AlertTriangle,
        label: 'Forecaster Offline',
      };

  const { Icon } = statusConfig;

  return (
    <div className={cn('flex items-center gap-3 px-3 py-2 rounded-lg border', statusConfig.bg, className)}>
      <div className="flex items-center gap-1.5">
        <div className={cn('w-2 h-2 rounded-full animate-pulse', statusConfig.pulse)} />
        <Icon size={13} className={statusConfig.color} />
      </div>
      <div className="flex flex-col">
        <span className={cn('text-xs font-semibold', statusConfig.color)}>{statusConfig.label}</span>
        <span className="text-[10px] text-muted-foreground">
          {health.model_name} · {health.device.toUpperCase()} · {health.n_scopes} scopes
        </span>
      </div>
      <div className="ml-auto flex items-center gap-1">
        <Cpu size={11} className="text-muted-foreground" />
        <span className="text-[10px] text-muted-foreground font-mono">{health.device}</span>
      </div>
    </div>
  );
}

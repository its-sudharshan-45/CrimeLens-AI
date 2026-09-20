import { cn } from '@/lib/utils';
import { ShieldAlert, ShieldCheck, AlertTriangle, ShieldX } from 'lucide-react';
import { confidenceToRisk, type RiskLevel } from '@/types/ai';

interface RiskLevelBadgeProps {
  confidence: number;
  className?: string;
}

const riskConfig: Record<
  RiskLevel,
  { label: string; bg: string; text: string; border: string; icon: typeof ShieldAlert }
> = {
  CRITICAL: {
    label: 'Critical Risk',
    bg: 'bg-red-500/10',
    text: 'text-red-400',
    border: 'border-red-500/20',
    icon: ShieldX,
  },
  HIGH: {
    label: 'High Risk',
    bg: 'bg-amber-500/10',
    text: 'text-amber-400',
    border: 'border-amber-500/20',
    icon: ShieldAlert,
  },
  MEDIUM: {
    label: 'Moderate Risk',
    bg: 'bg-blue-500/10',
    text: 'text-blue-400',
    border: 'border-blue-500/20',
    icon: AlertTriangle,
  },
  LOW: {
    label: 'Low Risk',
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    border: 'border-emerald-500/20',
    icon: ShieldCheck,
  },
};

export function RiskLevelBadge({ confidence, className }: RiskLevelBadgeProps) {
  const riskLevel = confidenceToRisk(confidence);
  const cfg = riskConfig[riskLevel];
  const Icon = cfg.icon;

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border',
        cfg.bg,
        cfg.text,
        cfg.border,
        className
      )}
    >
      <Icon size={13} />
      <span>{cfg.label}</span>
    </div>
  );
}

import { cn } from '@/lib/utils';

type BadgeVariant =
  | 'default' | 'emerald' | 'amber' | 'red' | 'blue' | 'purple' | 'slate'
  | 'outline-emerald' | 'outline-amber' | 'outline-red';

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
  dot?: boolean;
}

const variants: Record<BadgeVariant, string> = {
  default: 'bg-secondary text-muted-foreground border-border',
  emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  red: 'bg-red-500/10 text-red-400 border-red-500/20',
  blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  slate: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
  'outline-emerald': 'border-emerald-500/40 text-emerald-400',
  'outline-amber': 'border-amber-500/40 text-amber-400',
  'outline-red': 'border-red-500/40 text-red-400',
};

const dotColors: Record<BadgeVariant, string> = {
  default: 'bg-muted-foreground',
  emerald: 'bg-emerald-400',
  amber: 'bg-amber-400',
  red: 'bg-red-400',
  blue: 'bg-blue-400',
  purple: 'bg-purple-400',
  slate: 'bg-slate-400',
  'outline-emerald': 'bg-emerald-400',
  'outline-amber': 'bg-amber-400',
  'outline-red': 'bg-red-400',
};

export function Badge({ variant = 'default', children, className, dot = false }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border',
        variants[variant],
        className,
      )}
    >
      {dot && <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', dotColors[variant])} />}
      {children}
    </span>
  );
}

// ─── Domain-specific badge helpers ───────────────────────────────────────────

type CrimeStatus = 'OPEN' | 'UNDER_INVESTIGATION' | 'CLOSED' | 'ARCHIVED';
type Priority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
type InvestigationStatus =
  | 'OPEN'
  | 'UNDER_INVESTIGATION'
  | 'WAITING_FOR_EVIDENCE'
  | 'ON_HOLD'
  | 'CLOSED'
  | 'ARCHIVED';

export function CrimeStatusBadge({ status }: { status: CrimeStatus }) {
  const map: Record<CrimeStatus, { variant: BadgeVariant; label: string }> = {
    OPEN: { variant: 'emerald', label: 'Open' },
    UNDER_INVESTIGATION: { variant: 'amber', label: 'Under Investigation' },
    CLOSED: { variant: 'slate', label: 'Closed' },
    ARCHIVED: { variant: 'default', label: 'Archived' },
  };
  const { variant, label } = map[status] ?? { variant: 'default', label: status };
  return <Badge variant={variant} dot>{label}</Badge>;
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  const map: Record<Priority, { variant: BadgeVariant; label: string }> = {
    LOW: { variant: 'blue', label: 'Low' },
    MEDIUM: { variant: 'amber', label: 'Medium' },
    HIGH: { variant: 'red', label: 'High' },
    CRITICAL: { variant: 'red', label: 'Critical' },
  };
  const { variant, label } = map[priority] ?? { variant: 'default', label: priority };
  return <Badge variant={variant}>{label}</Badge>;
}

export function InvestigationStatusBadge({ status }: { status: InvestigationStatus | string }) {
  const map: Record<string, { variant: BadgeVariant; label: string }> = {
    OPEN: { variant: 'blue', label: 'Open' },
    UNDER_INVESTIGATION: { variant: 'emerald', label: 'Under Investigation' },
    WAITING_FOR_EVIDENCE: { variant: 'amber', label: 'Waiting for Evidence' },
    ON_HOLD: { variant: 'amber', label: 'On Hold' },
    CLOSED: { variant: 'slate', label: 'Closed' },
    ARCHIVED: { variant: 'default', label: 'Archived' },
    // Legacy seed values (display-only until data is re-seeded)
    ACTIVE: { variant: 'emerald', label: 'Under Investigation' },
    IN_PROGRESS: { variant: 'emerald', label: 'Under Investigation' },
    ASSIGNED: { variant: 'blue', label: 'Open' },
  };
  const { variant, label } = map[status] ?? { variant: 'default', label: status.replace(/_/g, ' ') };
  return <Badge variant={variant} dot>{label}</Badge>;
}

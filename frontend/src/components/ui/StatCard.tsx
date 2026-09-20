import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Skeleton } from './Skeleton';

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: { value: number; label?: string };
  className?: string;
  loading?: boolean;
  accent?: 'emerald' | 'amber' | 'red' | 'blue' | 'purple';
}

const accentMap = {
  emerald: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  amber: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  red: 'text-red-400 bg-red-500/10 border-red-500/20',
  blue: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  purple: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
};

export function StatCard({ label, value, icon, trend, className, loading = false, accent = 'emerald' }: StatCardProps) {
  if (loading) {
    return (
      <div className={cn('bg-card border border-border rounded-xl p-5 space-y-3', className)}>
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-3 w-20" />
      </div>
    );
  }

  const trendPositive = (trend?.value ?? 0) > 0;
  const trendNeutral = (trend?.value ?? 0) === 0;

  return (
    <div
      className={cn(
        'bg-card border border-border rounded-xl p-5 group hover:border-emerald-500/20 transition-all duration-200',
        className,
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{label}</p>
        {icon && (
          <div className={cn('p-2 rounded-lg border', accentMap[accent])}>
            {icon}
          </div>
        )}
      </div>
      <p className="text-3xl font-bold text-foreground tracking-tight">{value}</p>
      {trend && (
        <div className={cn(
          'flex items-center gap-1.5 mt-2 text-xs font-medium',
          trendPositive ? 'text-emerald-400' : trendNeutral ? 'text-muted-foreground' : 'text-red-400',
        )}>
          {trendPositive ? <TrendingUp size={12} /> : trendNeutral ? <Minus size={12} /> : <TrendingDown size={12} />}
          <span>{Math.abs(trend.value)}% {trend.label ?? 'vs last month'}</span>
        </div>
      )}
    </div>
  );
}

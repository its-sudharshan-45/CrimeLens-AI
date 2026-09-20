import React from 'react';
import { AlertCircle, CheckCircle, Info, AlertTriangle, X } from 'lucide-react';
import { cn } from '@/lib/utils';

type AlertVariant = 'info' | 'success' | 'warning' | 'error';

interface AlertProps {
  variant?: AlertVariant;
  title?: string;
  children: React.ReactNode;
  onClose?: () => void;
  className?: string;
}

const config: Record<AlertVariant, { icon: React.ReactNode; classes: string }> = {
  info: {
    icon: <Info size={15} />,
    classes: 'bg-blue-500/5 border-blue-500/20 text-blue-400',
  },
  success: {
    icon: <CheckCircle size={15} />,
    classes: 'bg-emerald-500/5 border-emerald-500/20 text-emerald-400',
  },
  warning: {
    icon: <AlertTriangle size={15} />,
    classes: 'bg-amber-500/5 border-amber-500/20 text-amber-400',
  },
  error: {
    icon: <AlertCircle size={15} />,
    classes: 'bg-red-500/5 border-red-500/20 text-red-400',
  },
};

export function Alert({ variant = 'info', title, children, onClose, className }: AlertProps) {
  const { icon, classes } = config[variant];

  return (
    <div className={cn('flex gap-3 p-4 rounded-xl border', classes, className)} role="alert">
      <span className="shrink-0 mt-0.5">{icon}</span>
      <div className="flex-1 min-w-0">
        {title && <p className="font-medium text-sm mb-0.5">{title}</p>}
        <div className="text-sm opacity-90">{children}</div>
      </div>
      {onClose && (
        <button onClick={onClose} className="shrink-0 opacity-60 hover:opacity-100 transition-opacity mt-0.5">
          <X size={14} />
        </button>
      )}
    </div>
  );
}

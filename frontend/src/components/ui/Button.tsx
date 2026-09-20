import React from 'react';
import { cn } from '@/lib/utils';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline' | 'destructive';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  loading?: boolean;
  children: React.ReactNode;
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  className,
  children,
  ...props
}: ButtonProps) {
  const base =
    'inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-background disabled:opacity-50 disabled:cursor-not-allowed select-none';

  const variants = {
    primary:
      'bg-emerald-500 hover:bg-emerald-600 active:bg-emerald-700 text-charcoal-950 focus:ring-emerald-500 shadow-sm',
    secondary:
      'bg-secondary hover:bg-secondary/80 text-foreground focus:ring-secondary border border-border',
    ghost:
      'hover:bg-secondary text-foreground focus:ring-secondary',
    outline:
      'border border-border hover:bg-secondary text-foreground focus:ring-emerald-500',
    destructive:
      'bg-destructive hover:bg-destructive/90 text-white focus:ring-destructive',
  };

  const sizes = {
    sm: 'h-8 px-3 text-xs',
    md: 'h-10 px-4 text-sm',
    lg: 'h-11 px-6 text-sm',
    icon: 'h-10 w-10 p-0',
  };

  return (
    <button
      className={cn(base, variants[variant], sizes[size], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin shrink-0" />
      )}
      {children}
    </button>
  );
}

import React from 'react';
import { cn } from '@/lib/utils';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, ...props }, ref) => {
    return (
      <div className="relative">
        <input
          ref={ref}
          className={cn(
            'flex h-10 w-full rounded-lg border bg-input px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground',
            'border-border',
            'transition-colors duration-150',
            'focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500/60',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'file:border-0 file:bg-transparent file:text-sm file:font-medium',
            error && 'border-destructive focus:ring-destructive/30 focus:border-destructive',
            className
          )}
          {...props}
        />
        {error && (
          <p className="mt-1.5 text-xs text-destructive">{error}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

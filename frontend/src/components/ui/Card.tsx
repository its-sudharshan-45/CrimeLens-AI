import React from 'react';
import { cn } from '@/lib/utils';

interface CardProps {
  className?: string;
  children: React.ReactNode;
  hover?: boolean;
}
export function Card({ className, children, hover = false }: CardProps) {
  return (
    <div
      className={cn(
        'bg-card border border-border rounded-xl',
        hover && 'transition-all duration-200 hover:border-emerald-500/30 hover:shadow-glow-emerald',
        className,
      )}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps { className?: string; children: React.ReactNode }
export function CardHeader({ className, children }: CardHeaderProps) {
  return <div className={cn('px-6 py-4 border-b border-border', className)}>{children}</div>;
}

interface CardTitleProps { className?: string; children: React.ReactNode }
export function CardTitle({ className, children }: CardTitleProps) {
  return <h3 className={cn('text-base font-semibold text-foreground', className)}>{children}</h3>;
}

interface CardDescriptionProps { className?: string; children: React.ReactNode }
export function CardDescription({ className, children }: CardDescriptionProps) {
  return <p className={cn('text-sm text-muted-foreground mt-0.5', className)}>{children}</p>;
}

interface CardContentProps { className?: string; children: React.ReactNode }
export function CardContent({ className, children }: CardContentProps) {
  return <div className={cn('px-6 py-4', className)}>{children}</div>;
}

interface CardFooterProps { className?: string; children: React.ReactNode }
export function CardFooter({ className, children }: CardFooterProps) {
  return (
    <div className={cn('px-6 py-3 border-t border-border flex items-center', className)}>
      {children}
    </div>
  );
}

import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  side?: 'right' | 'left';
  width?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  className?: string;
}

const widths = {
  sm: 'w-80',
  md: 'w-[480px]',
  lg: 'w-[640px]',
};

export function Drawer({
  open, onClose, title, description,
  side = 'right', width = 'md', children, className,
}: DrawerProps) {
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    if (open) {
      document.addEventListener('keydown', handleKey);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity duration-300',
          open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none',
        )}
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className={cn(
          'fixed top-0 z-50 h-full bg-card border-border shadow-card-lg transition-transform duration-300 ease-out flex flex-col',
          side === 'right' ? 'right-0 border-l' : 'left-0 border-r',
          widths[width],
          side === 'right'
            ? open ? 'translate-x-0' : 'translate-x-full'
            : open ? 'translate-x-0' : '-translate-x-full',
          className,
        )}
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-border shrink-0">
          <div>
            {title && <h2 className="text-base font-semibold text-foreground">{title}</h2>}
            {description && <p className="text-sm text-muted-foreground mt-0.5">{description}</p>}
          </div>
          <button
            onClick={onClose}
            className="ml-4 shrink-0 text-muted-foreground hover:text-foreground transition-colors p-1 rounded-md hover:bg-secondary"
            aria-label="Close panel"
          >
            <X size={16} />
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
      </div>
    </>
  );
}

import { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DropdownOption {
  label: string;
  value: string;
}

interface DropdownProps {
  value: string;
  onChange: (value: string) => void;
  options: DropdownOption[];
  placeholder?: string;
  className?: string;
  id?: string;
  disabled?: boolean;
}

export function Dropdown({
  value, onChange, options, placeholder = 'Select…', className, id, disabled = false,
}: DropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const selected = options.find((o) => o.value === value);

  return (
    <div ref={ref} className={cn('relative', className)}>
      <button
        id={id}
        type="button"
        onClick={() => !disabled && setOpen((p) => !p)}
        disabled={disabled}
        className={cn(
          'h-9 w-full flex items-center justify-between gap-2 px-3 bg-secondary border border-border rounded-lg text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500/50 transition-colors',
          disabled && 'opacity-50 cursor-not-allowed',
          !disabled && 'hover:border-emerald-500/40',
        )}
      >
        <span className={cn(!selected && 'text-muted-foreground')}>
          {selected?.label ?? placeholder}
        </span>
        <ChevronDown size={13} className={cn('text-muted-foreground transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute top-full mt-1 left-0 right-0 z-50 bg-card border border-border rounded-lg shadow-card-lg overflow-hidden">
          <div className="max-h-56 overflow-y-auto py-1">
            {placeholder && (
              <button
                className="w-full px-3 py-2 text-left text-sm text-muted-foreground hover:bg-secondary transition-colors"
                onClick={() => { onChange(''); setOpen(false); }}
              >
                {placeholder}
              </button>
            )}
            {options.map((opt) => (
              <button
                key={opt.value}
                className={cn(
                  'w-full px-3 py-2 text-left text-sm hover:bg-secondary transition-colors',
                  opt.value === value ? 'text-emerald-400 bg-emerald-500/5' : 'text-foreground',
                )}
                onClick={() => { onChange(opt.value); setOpen(false); }}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

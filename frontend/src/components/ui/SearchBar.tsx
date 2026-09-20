import { Search, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useEffect, useRef, useState } from 'react';

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  debounce?: number;
  className?: string;
  id?: string;
}

export function SearchBar({
  value,
  onChange,
  placeholder = 'Search…',
  debounce = 300,
  className,
  id = 'search-bar',
}: SearchBarProps) {
  const [local, setLocal] = useState(value);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    setLocal(value);
  }, [value]);

  const handle = (v: string) => {
    setLocal(v);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => onChange(v), debounce);
  };

  return (
    <div className={cn('relative flex items-center', className)}>
      <Search
        size={14}
        className="absolute left-3 text-muted-foreground pointer-events-none"
      />
      <input
        id={id}
        type="text"
        value={local}
        onChange={(e) => handle(e.target.value)}
        placeholder={placeholder}
        className="h-9 w-full pl-9 pr-8 bg-secondary border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-colors"
      />
      {local && (
        <button
          onClick={() => handle('')}
          className="absolute right-2.5 text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Clear search"
        >
          <X size={13} />
        </button>
      )}
    </div>
  );
}

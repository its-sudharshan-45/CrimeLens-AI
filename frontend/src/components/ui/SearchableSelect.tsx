import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { Check, ChevronDown, Search } from 'lucide-react';

import { cn } from '@/lib/utils';

export interface SearchableOption {
  value: string;
  label: string;
  /** Optional secondary line, e.g. model-coverage information. */
  description?: string;
  /** Extra text that should match the search box but is not displayed. */
  keywords?: string;
}

interface SearchableSelectProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  options: SearchableOption[];
  placeholder: string;
  searchPlaceholder?: string;
  emptyMessage?: string;
  disabled?: boolean;
  className?: string;
}

function normalise(value: string) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

/**
 * Accessible, searchable single-select combobox.
 *
 * Native <select> elements cannot be filtered, so the location pickers use
 * this component instead. It keeps full keyboard support and only renders the
 * options that match the current query.
 */
export function SearchableSelect({
  id,
  value,
  onChange,
  options,
  placeholder,
  searchPlaceholder = 'Search…',
  emptyMessage = 'No matches found',
  disabled = false,
  className,
}: SearchableSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listboxId = useId();

  const selected = useMemo(() => options.find((option) => option.value === value), [options, value]);

  const filtered = useMemo(() => {
    const needle = normalise(query);
    if (!needle) return options;
    return options.filter((option) =>
      normalise(`${option.label} ${option.description ?? ''} ${option.keywords ?? ''}`).includes(needle),
    );
  }, [options, query]);

  useEffect(() => {
    if (!open) return undefined;
    const handlePointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
        setQuery('');
      }
    };
    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const selectedIndex = filtered.findIndex((option) => option.value === value);
    setActiveIndex(selectedIndex >= 0 ? selectedIndex : 0);
  }, [open, filtered, value]);

  const openList = () => {
    if (disabled) return;
    setOpen(true);
    setQuery('');
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  const closeList = () => {
    setOpen(false);
    setQuery('');
  };

  const selectOption = (nextValue: string) => {
    onChange(nextValue);
    closeList();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      if (!open) {
        openList();
        return;
      }
      setActiveIndex((index) => Math.min(index + 1, Math.max(filtered.length - 1, 0)));
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      if (!open) {
        openList();
        return;
      }
      setActiveIndex((index) => Math.max(index - 1, 0));
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      if (!open) {
        openList();
        return;
      }
      const option = filtered[activeIndex];
      if (option) selectOption(option.value);
      return;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      closeList();
      return;
    }
    if (event.key === 'Tab') {
      setOpen(false);
      setQuery('');
    }
  };

  const activeOption = filtered[activeIndex];

  return (
    <div ref={rootRef} className={cn('relative', className)}>
      <div
        className={cn(
          'flex h-11 items-center gap-2 rounded-lg border border-border bg-secondary px-3',
          'focus-within:border-emerald-500/60 focus-within:ring-2 focus-within:ring-emerald-500/30',
          disabled && 'cursor-not-allowed opacity-50',
        )}
      >
        <Search size={14} className="shrink-0 text-muted-foreground" aria-hidden="true" />
        <input
          ref={inputRef}
          id={id}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={open && activeOption ? `${listboxId}-option-${activeIndex}` : undefined}
          autoComplete="off"
          value={open ? query : (selected?.label ?? '')}
          placeholder={open ? searchPlaceholder : placeholder}
          disabled={disabled}
          onChange={(event) => setQuery(event.target.value)}
          onFocus={openList}
          onClick={() => {
            if (!open) openList();
          }}
          onKeyDown={handleKeyDown}
          className="h-full w-full min-w-0 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none disabled:cursor-not-allowed"
        />
        <button
          type="button"
          tabIndex={-1}
          disabled={disabled}
          aria-label={open ? 'Close options' : 'Open options'}
          onClick={() => (open ? closeList() : openList())}
          className="shrink-0 rounded p-0.5 text-muted-foreground transition-colors hover:text-foreground disabled:cursor-not-allowed"
        >
          <ChevronDown size={15} className={cn('transition-transform', open && 'rotate-180')} aria-hidden="true" />
        </button>
      </div>

      {open && (
        <ul
          id={listboxId}
          role="listbox"
          aria-label={placeholder}
          className="absolute z-30 mt-1.5 max-h-72 w-full overflow-y-auto rounded-lg border border-border bg-card p-1 shadow-xl shadow-black/20"
        >
          {filtered.length === 0 && (
            <li className="px-3 py-2.5 text-xs text-muted-foreground">{emptyMessage}</li>
          )}
          {filtered.map((option, index) => {
            const isSelected = option.value === value;
            const isActive = index === activeIndex;
            return (
              <li
                key={option.value}
                id={`${listboxId}-option-${index}`}
                role="option"
                aria-selected={isSelected}
                onMouseDown={(event) => event.preventDefault()}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => selectOption(option.value)}
                className={cn(
                  'flex cursor-pointer items-start gap-2 rounded-md px-2.5 py-2 text-sm',
                  isActive ? 'bg-emerald-500/10 text-foreground' : 'text-foreground/90',
                  isSelected && 'font-medium',
                )}
              >
                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center">
                  {isSelected && <Check size={13} className="text-emerald-400" aria-hidden="true" />}
                </span>
                <span className="min-w-0">
                  <span className="block truncate">{option.label}</span>
                  {option.description && (
                    <span className="mt-0.5 block text-[11px] font-normal leading-snug text-muted-foreground">
                      {option.description}
                    </span>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

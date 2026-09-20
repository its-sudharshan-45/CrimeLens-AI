import { TooltipProps } from 'recharts';

export function ChartTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="bg-card border border-border rounded-lg p-3 shadow-xl backdrop-blur-md text-xs space-y-1 z-50">
      {label && <p className="font-semibold text-foreground border-b border-border pb-1 mb-1">{label}</p>}
      {payload.map((item, idx) => (
        <div key={idx} className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color || '#10b981' }} />
          <span className="text-muted-foreground capitalize">{item.name || item.dataKey}:</span>
          <span className="font-mono font-semibold text-foreground ml-auto">
            {typeof item.value === 'number' ? item.value.toLocaleString() : item.value}
          </span>
        </div>
      ))}
    </div>
  );
}

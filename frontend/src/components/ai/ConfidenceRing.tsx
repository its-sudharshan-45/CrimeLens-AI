import { cn } from '@/lib/utils';

interface ConfidenceRingProps {
  confidence: number; // 0.0 to 1.0
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

export function ConfidenceRing({
  confidence,
  size = 'md',
  showLabel = true,
  className,
}: ConfidenceRingProps) {
  const percentage = Math.round(confidence * 100);

  const dimensions = {
    sm: { size: 44, stroke: 4, font: 'text-xs' },
    md: { size: 72, stroke: 6, font: 'text-sm font-bold' },
    lg: { size: 100, stroke: 8, font: 'text-xl font-bold' },
  }[size];

  const radius = (dimensions.size - dimensions.stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (confidence * circumference);

  const color =
    confidence >= 0.8
      ? '#10b981' // emerald
      : confidence >= 0.6
      ? '#f59e0b' // amber
      : '#ef4444'; // red

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)}>
      <svg
        width={dimensions.size}
        height={dimensions.size}
        className="transform -rotate-90"
      >
        {/* Track */}
        <circle
          cx={dimensions.size / 2}
          cy={dimensions.size / 2}
          r={radius}
          stroke="hsl(var(--muted))"
          strokeWidth={dimensions.stroke}
          fill="transparent"
        />
        {/* Progress Arc */}
        <circle
          cx={dimensions.size / 2}
          cy={dimensions.size / 2}
          r={radius}
          stroke={color}
          strokeWidth={dimensions.stroke}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="transparent"
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      {showLabel && (
        <span className={cn('absolute font-mono text-foreground', dimensions.font)}>
          {percentage}%
        </span>
      )}
    </div>
  );
}

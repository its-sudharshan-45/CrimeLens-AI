interface ProbabilityDistributionProps {
  probabilities: Record<string, number>;
  predictedDomain: string;
}

export function ProbabilityDistribution({
  probabilities,
  predictedDomain,
}: ProbabilityDistributionProps) {
  const entries = Object.entries(probabilities).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        Class Probability Distribution
      </h4>
      <div className="space-y-2">
        {entries.map(([label, prob]) => {
          const isTop = label === predictedDomain;
          const pct = Math.round(prob * 100);

          return (
            <div key={label} className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className={isTop ? 'font-semibold text-emerald-400' : 'text-muted-foreground'}>
                  {label} {isTop && '(Predicted)'}
                </span>
                <span className="font-mono text-foreground font-medium">{pct}%</span>
              </div>
              <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    isTop ? 'bg-emerald-500' : 'bg-secondary-foreground/30'
                  }`}
                  style={{ width: `${Math.max(pct, 1)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

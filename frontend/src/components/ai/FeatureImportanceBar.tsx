import { FeatureAttribution } from '@/types/ai';

interface FeatureImportanceBarProps {
  features: FeatureAttribution[];
  title?: string;
  maxCount?: number;
}

export function FeatureImportanceBar({
  features,
  title = 'Captum XAI Feature Attribution',
  maxCount = 8,
}: FeatureImportanceBarProps) {
  const topFeatures = features.slice(0, maxCount);
  const maxScore = Math.max(...topFeatures.map((f) => Math.abs(f.attribution_score)), 0.0001);

  return (
    <div className="space-y-3">
      {title && <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{title}</h4>}
      <div className="space-y-2.5">
        {topFeatures.map((feat) => {
          const pct = Math.round((Math.abs(feat.attribution_score) / maxScore) * 100);
          return (
            <div key={feat.feature_name} className="space-y-1">
              <div className="flex justify-between text-xs font-medium">
                <span className="text-foreground truncate max-w-[200px]">{feat.feature_name}</span>
                <span className="font-mono text-emerald-400">{feat.attribution_score.toFixed(4)}</span>
              </div>
              <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 rounded-full transition-all duration-700 ease-out"
                  style={{ width: `${Math.max(pct, 2)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

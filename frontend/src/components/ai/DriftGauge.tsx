import { DriftStatusResponse } from '@/types/ai';
import { AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';

interface DriftGaugeProps {
  drift?: DriftStatusResponse;
}

export function DriftGauge({ drift }: DriftGaugeProps) {
  if (!drift) return null;

  const scorePct = Math.round(drift.drift_score * 100);

  const levelColor =
    drift.overall_level === 'LOW'
      ? { text: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20', icon: CheckCircle }
      : drift.overall_level === 'MEDIUM'
      ? { text: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20', icon: AlertTriangle }
      : { text: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20', icon: AlertCircle };

  const Icon = levelColor.icon;

  return (
    <div className="bg-card border border-border rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-foreground">Model Drift Status</h4>
          <p className="text-xs text-muted-foreground">Sample Size: {drift.sample_size} records</p>
        </div>
        <div
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-semibold ${levelColor.bg} ${levelColor.text}`}
        >
          <Icon size={14} />
          <span>{drift.overall_level} DRIFT</span>
        </div>
      </div>

      <div className="space-y-1.5">
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Drift Score Metric</span>
          <span className={`font-mono font-semibold ${levelColor.text}`}>{scorePct}%</span>
        </div>
        <div className="h-2 bg-secondary rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${
              drift.overall_level === 'LOW'
                ? 'bg-emerald-500'
                : drift.overall_level === 'MEDIUM'
                ? 'bg-amber-500'
                : 'bg-red-500'
            }`}
            style={{ width: `${Math.max(scorePct, 2)}%` }}
          />
        </div>
      </div>

      {drift.feature_drift.affected_features.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">Drifted Features:</p>
          <div className="flex flex-wrap gap-1.5">
            {drift.feature_drift.affected_features.map((feat) => (
              <span
                key={feat}
                className="px-2 py-0.5 rounded text-[11px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20"
              >
                {feat}
              </span>
            ))}
          </div>
        </div>
      )}

      {drift.warnings.length > 0 && (
        <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/15 text-xs text-red-400 space-y-1">
          <p className="font-semibold">Drift Alerts:</p>
          <ul className="list-disc list-inside space-y-0.5 text-[11px]">
            {drift.warnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

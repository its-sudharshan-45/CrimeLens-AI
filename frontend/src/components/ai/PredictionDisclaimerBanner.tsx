import { AlertTriangle, ShieldAlert } from 'lucide-react';

interface PredictionDisclaimerBannerProps {
  customText?: string;
  compact?: boolean;
}

export function PredictionDisclaimerBanner({
  customText,
  compact = false,
}: PredictionDisclaimerBannerProps) {
  const text =
    customText ||
    'These results are probabilistic estimates based on historical crime patterns. They are not definitive predictions, evidence, or conclusions about individuals. Investigative decisions require independent human verification.';

  if (compact) {
    return (
      <div className="flex items-start gap-2.5 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs leading-relaxed">
        <AlertTriangle size={15} className="text-amber-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-amber-200 mr-1.5">⚠ Predictive Aid:</span>
          {text}
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-200">
      <div className="flex items-center gap-2 mb-1.5">
        <ShieldAlert size={18} className="text-amber-400" />
        <h4 className="text-xs font-bold uppercase tracking-wider text-amber-300">
          ⚠ Predictive Aid & Human Verification Mandatory
        </h4>
      </div>
      <p className="text-xs text-amber-100/90 leading-relaxed">
        {text}
      </p>
      <div className="mt-2 pt-2 border-t border-amber-500/20 flex flex-wrap items-center gap-4 text-[11px] text-amber-300/80">
        <span>• Probabilistic Pattern Analysis Only</span>
        <span>• Zero Individual Suspect Profiling</span>
        <span>• For Law Enforcement Resource Planning</span>
      </div>
    </div>
  );
}

import { CrimePredictionResponse } from '@/types/ai';
import { ConfidenceRing } from './ConfidenceRing';
import { RiskLevelBadge } from './RiskLevelBadge';
import { ProbabilityDistribution } from './ProbabilityDistribution';
import { Brain, Cpu, Clock, Hash } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface PredictionResultCardProps {
  prediction: CrimePredictionResponse;
  onRunXAI?: () => void;
  isExplainLoading?: boolean;
}

export function PredictionResultCard({
  prediction,
  onRunXAI,
  isExplainLoading,
}: PredictionResultCardProps) {
  return (
    <div className="bg-card border border-emerald-500/30 rounded-2xl p-6 space-y-6 shadow-xl shadow-emerald-500/5 animate-fade-in">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400">
              <Brain size={18} />
            </span>
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
              AI Prediction Output
            </span>
          </div>
          <h2 className="text-2xl font-bold text-foreground tracking-tight">
            {prediction.predicted_domain}
          </h2>
          <p className="text-xs text-muted-foreground">
            Classified via {prediction.model_name} ({prediction.model_version})
          </p>
        </div>

        <div className="flex items-center gap-4">
          <ConfidenceRing confidence={prediction.confidence_score} size="lg" />
          <div className="flex flex-col gap-1.5">
            <RiskLevelBadge confidence={prediction.confidence_score} />
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-mono">
              <Clock size={12} />
              <span>{prediction.execution_time_ms} ms</span>
            </div>
          </div>
        </div>
      </div>

      {/* Metadata Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-secondary/30 rounded-xl p-3 text-xs">
        <div>
          <span className="text-muted-foreground block text-[10px] uppercase">Prediction ID</span>
          <span className="font-mono text-foreground truncate block font-medium">
            {prediction.prediction_id ? prediction.prediction_id.slice(0, 8) + '...' : 'Generated'}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[10px] uppercase">Domain Code</span>
          <span className="font-mono text-foreground font-medium flex items-center gap-1">
            <Hash size={11} /> {prediction.domain_code}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[10px] uppercase">Confidence</span>
          <span className="font-mono text-emerald-400 font-bold">
            {(prediction.confidence_score * 100).toFixed(1)}%
          </span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[10px] uppercase">Model</span>
          <span className="font-medium text-foreground truncate flex items-center gap-1">
            <Cpu size={11} /> {prediction.model_name}
          </span>
        </div>
      </div>

      {/* Probability Distribution */}
      {prediction.probabilities && Object.keys(prediction.probabilities).length > 0 && (
        <ProbabilityDistribution
          probabilities={prediction.probabilities}
          predictedDomain={prediction.predicted_domain}
        />
      )}

      {/* XAI CTA Button */}
      {onRunXAI && (
        <div className="border-t border-border pt-4 flex justify-end">
          <Button
            onClick={onRunXAI}
            loading={isExplainLoading}
            variant="outline"
            size="sm"
            className="border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
          >
            <Brain size={14} className="mr-1.5" /> Explain Prediction (Captum XAI)
          </Button>
        </div>
      )}
    </div>
  );
}

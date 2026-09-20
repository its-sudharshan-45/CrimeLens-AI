import { ModelVersionInfo } from '@/types/ai';
import { Cpu, CheckCircle2, Archive } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';

interface ModelVersionCardProps {
  model: ModelVersionInfo;
  isCurrent?: boolean;
}

export function ModelVersionCard({ model, isCurrent }: ModelVersionCardProps) {
  return (
    <div
      className={`bg-card border rounded-xl p-5 space-y-4 transition-all ${
        isCurrent
          ? 'border-emerald-500/40 bg-emerald-500/5 shadow-lg shadow-emerald-500/5'
          : 'border-border hover:border-border/80'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <div
            className={`p-2 rounded-lg ${
              isCurrent ? 'bg-emerald-500/20 text-emerald-400' : 'bg-secondary text-muted-foreground'
            }`}
          >
            <Cpu size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-bold text-foreground">{model.model_name}</h4>
              {isCurrent && <Badge variant="emerald">Active</Badge>}
            </div>
            <p className="text-xs text-muted-foreground font-mono">v{model.version}</p>
          </div>
        </div>

        <div className="flex items-center gap-1 text-xs">
          {model.status === 'Active' ? (
            <span className="flex items-center gap-1 text-emerald-400 font-medium">
              <CheckCircle2 size={12} /> Active
            </span>
          ) : (
            <span className="flex items-center gap-1 text-muted-foreground">
              <Archive size={12} /> Archived
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs border-t border-border/50 pt-3">
        <div>
          <span className="text-muted-foreground">Framework:</span>
          <p className="font-medium text-foreground truncate">{model.framework_version}</p>
        </div>
        <div>
          <span className="text-muted-foreground">Dataset Hash:</span>
          <p className="font-mono text-muted-foreground truncate">{model.dataset_hash}</p>
        </div>
      </div>

      {Object.keys(model.accuracy_metrics).length > 0 && (
        <div className="border-t border-border/50 pt-3 space-y-1.5">
          <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
            Accuracy Metrics
          </span>
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(model.accuracy_metrics).map(([k, v]) => (
              <div key={k} className="bg-secondary/40 rounded p-1.5 text-center">
                <span className="text-[10px] text-muted-foreground uppercase block">{k}</span>
                <span className="font-mono text-xs font-semibold text-emerald-400">
                  {typeof v === 'number' ? (v <= 1 ? `${(v * 100).toFixed(1)}%` : v) : v}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

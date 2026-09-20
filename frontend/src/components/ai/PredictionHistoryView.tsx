import { useState } from 'react';
import {
  History,
  Clock,
  Cpu,
  RefreshCw,
  Filter,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { PredictionDisclaimerBanner } from '@/components/ai/PredictionDisclaimerBanner';
import { usePredictionHistory } from '@/hooks/usePredictions';

const PREDICTION_TYPES = [
  { value: '', label: 'All Prediction Types' },
  { value: 'HOTSPOT', label: 'City Hotspots (CNN)' },
  { value: 'TREND', label: 'Temporal Forecast (GRU)' },
  { value: 'SIMILAR_CASE', label: 'Investigation Priorities' },
];

export function PredictionHistoryView() {
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(10);
  const [selectedType, setSelectedType] = useState<string>('');

  const { data, isLoading, isError, error, refetch } = usePredictionHistory(
    page,
    pageSize,
    selectedType || undefined
  );

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  const getTypeBadge = (type: string) => {
    switch (type.toUpperCase()) {
      case 'HOTSPOT':
        return <Badge variant="emerald">Hotspot (CNN)</Badge>;
      case 'TREND':
        return <Badge variant="blue">Temporal (GRU)</Badge>;
      case 'SIMILAR_CASE':
        return <Badge variant="purple">Investigation Lead</Badge>;
      default:
        return <Badge variant="default">{type}</Badge>;
    }
  };

  const getConfidenceBadge = (confidence: number) => {
    const pct = Math.round(confidence * 100);
    const color =
      pct >= 85
        ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
        : pct >= 70
        ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
        : 'text-rose-400 bg-rose-500/10 border-rose-500/20';

    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-bold border ${color}`}>
        {pct}%
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <PredictionDisclaimerBanner
        customText="All past predictions are logged with full model lineage, inference duration, and confidence thresholds for complete algorithmic accountability and auditability."
      />

      {/* Filter and Action Bar */}
      <Card className="p-4 bg-card/60 backdrop-blur border border-border">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <History size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-foreground">AI Prediction Audit History</h2>
                <Badge variant="default">{data?.total ?? 0} Recorded</Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Complete query logs, confidence scores, execution times, and model versions
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs">
              <Filter size={12} className="text-muted-foreground" />
              <select
                value={selectedType}
                onChange={(e) => {
                  setSelectedType(e.target.value);
                  setPage(1);
                }}
                className="h-8 rounded-lg bg-secondary border border-border px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                {PREDICTION_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isLoading}
              className="h-8 text-xs"
            >
              <RefreshCw size={12} className={`mr-1.5 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>
      </Card>

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <Card key={i} className="p-4 animate-pulse space-y-2">
              <div className="h-4 bg-muted rounded w-1/4" />
              <div className="h-3 bg-muted rounded w-3/4" />
            </Card>
          ))}
        </div>
      )}

      {/* Error state */}
      {isError && (
        <Card className="p-6 text-center text-red-400 space-y-2 border-red-500/30">
          <p className="text-sm font-semibold">Failed to load prediction history</p>
          <p className="text-xs text-muted-foreground">{(error as Error)?.message}</p>
        </Card>
      )}

      {/* Empty State */}
      {!isLoading && !isError && data && data.items.length === 0 && (
        <Card className="p-12 text-center flex flex-col items-center justify-center min-h-[250px] space-y-3">
          <div className="w-12 h-12 rounded-xl bg-secondary/80 flex items-center justify-center text-muted-foreground">
            <History size={24} />
          </div>
          <h3 className="text-sm font-bold text-foreground">No Prediction Records Found</h3>
          <p className="text-xs text-muted-foreground max-w-sm">
            Run a city hotspot forecast, temporal risk projection, or investigative lead query to populate history.
          </p>
        </Card>
      )}

      {/* History Items List */}
      {!isLoading && !isError && data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((item) => (
            <Card
              key={item.id}
              className="p-4 transition-all hover:border-emerald-500/40 relative overflow-hidden"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    {getTypeBadge(item.prediction_type)}
                    <h3 className="text-sm font-bold text-foreground">{item.prediction_label}</h3>
                  </div>
                  <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground pt-1">
                    <span className="flex items-center gap-1">
                      <Cpu size={12} className="text-muted-foreground" />
                      {item.model_name} ({item.model_version})
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock size={12} className="text-muted-foreground" />
                      {item.execution_time_ms} ms latency
                    </span>
                    <span>
                      {new Date(item.created_at).toLocaleString('en-IN', {
                        dateStyle: 'medium',
                        timeStyle: 'short',
                      })}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3 sm:self-center self-end">
                  <div className="text-right">
                    <div className="text-[10px] uppercase text-muted-foreground font-medium">
                      Confidence
                    </div>
                    {getConfidenceBadge(item.confidence_score)}
                  </div>
                </div>
              </div>
            </Card>
          ))}

          {/* Pagination Controls */}
          <div className="flex items-center justify-between pt-3 text-xs text-muted-foreground">
            <div>
              Showing {(page - 1) * pageSize + 1} to{' '}
              {Math.min(page * pageSize, data.total)} of {data.total} records
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="h-8 px-2.5 text-xs"
              >
                <ChevronLeft size={14} className="mr-1" />
                Previous
              </Button>
              <span className="font-mono text-foreground font-medium px-1">
                {page} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="h-8 px-2.5 text-xs"
              >
                Next
                <ChevronRight size={14} className="ml-1" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

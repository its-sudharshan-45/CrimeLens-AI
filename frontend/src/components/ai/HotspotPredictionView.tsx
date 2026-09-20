import { useState } from 'react';
import {
  MapPin,
  AlertTriangle,
  RefreshCw,
  Filter,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { PredictionDisclaimerBanner } from '@/components/ai/PredictionDisclaimerBanner';
import { useHotspots } from '@/hooks/usePredictions';

const CRIME_TYPES = ['All', 'Theft', 'Burglary', 'Assault', 'Robbery', 'Cybercrime'];

export function HotspotPredictionView() {
  const [topN, setTopN] = useState<number>(5);
  const [crimeType, setCrimeType] = useState<string>('All');

  const { data, isLoading, isError, error, refetch } = useHotspots({
    top_n: topN,
    crime_type: crimeType,
  });

  const getRiskBadgeVariant = (level: string) => {
    switch (level.toLowerCase()) {
      case 'high':
        return 'red';
      case 'medium':
        return 'amber';
      case 'low':
      default:
        return 'emerald';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Global Ethics Disclaimer */}
      <PredictionDisclaimerBanner customText={data?.disclaimer} />

      {/* Filter / Control Header */}
      <Card className="p-4 bg-card/60 backdrop-blur border border-border">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <MapPin size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-foreground">City Hotspot Risk Forecasting</h2>
                <Badge variant="emerald">Phase 4 CNN</Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Spatio-temporal risk evaluation across 29 validated cities (7-Day Horizon)
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Top-N Selector */}
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-muted-foreground">Top:</span>
              <select
                value={topN}
                onChange={(e) => setTopN(Number(e.target.value))}
                className="h-8 rounded-lg bg-secondary border border-border px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                <option value={5}>Top 5 Cities</option>
                <option value={10}>Top 10 Cities</option>
                <option value={15}>Top 15 Cities</option>
                <option value={20}>Top 20 Cities</option>
                <option value={29}>All 29 Cities</option>
              </select>
            </div>

            {/* Crime Type Filter */}
            <div className="flex items-center gap-1.5 text-xs">
              <Filter size={12} className="text-muted-foreground" />
              <select
                value={crimeType}
                onChange={(e) => setCrimeType(e.target.value)}
                className="h-8 rounded-lg bg-secondary border border-border px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                {CRIME_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
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

      {/* Loading state */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <Card key={i} className="p-4 space-y-3 animate-pulse">
              <div className="h-4 bg-muted rounded w-1/3" />
              <div className="h-8 bg-muted rounded w-2/3" />
              <div className="h-3 bg-muted rounded w-full" />
            </Card>
          ))}
        </div>
      )}

      {/* Error state */}
      {isError && (
        <Card className="p-6 text-center text-red-400 space-y-2 border-red-500/30">
          <AlertTriangle size={24} className="mx-auto text-red-400" />
          <p className="text-sm font-semibold">Failed to load hotspot predictions</p>
          <p className="text-xs text-muted-foreground">{(error as Error)?.message}</p>
        </Card>
      )}

      {/* Hotspots Content */}
      {data && data.hotspots && (
        <div className="space-y-6">
          {/* Summary Metric Ribbon */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-3.5 rounded-xl bg-secondary/50 border border-border">
              <div className="text-[11px] font-medium text-muted-foreground">Forecast Horizon</div>
              <div className="text-base font-bold text-foreground mt-0.5">
                Next {data.forecast_horizon_days} Days
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-secondary/50 border border-border">
              <div className="text-[11px] font-medium text-muted-foreground">Cities Evaluated</div>
              <div className="text-base font-bold text-foreground mt-0.5">
                {data.total_cities_evaluated || 29} Cities
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-secondary/50 border border-border">
              <div className="text-[11px] font-medium text-muted-foreground">Top Risk City</div>
              <div className="text-base font-bold text-rose-400 mt-0.5">
                {data.hotspots[0]?.city} ({data.hotspots[0]?.predicted_crimes} crimes)
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-secondary/50 border border-border">
              <div className="text-[11px] font-medium text-muted-foreground">Model Confidence</div>
              <div className="text-base font-bold text-emerald-400 mt-0.5">
                {(data.hotspots[0]?.confidence_score * 100).toFixed(0)}%
              </div>
            </div>
          </div>

          {/* Top Risk Areas Grid */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Ranked Hotspot Areas (Top {data.hotspots.length})
              </h3>
              <span className="text-[11px] text-muted-foreground">
                Higher score indicates greater relative incident density
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.hotspots.map((item) => (
                <Card
                  key={item.city}
                  className="p-4 transition-all hover:border-emerald-500/40 relative overflow-hidden flex flex-col justify-between"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-lg bg-secondary flex items-center justify-center font-mono font-bold text-xs text-foreground border border-border">
                        #{item.rank}
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-foreground">{item.city}</h4>
                        <span className="text-[11px] text-muted-foreground">
                          {data.forecast_horizon_days}-Day Projection
                        </span>
                      </div>
                    </div>
                    <Badge variant={getRiskBadgeVariant(item.risk_level)}>
                      {item.risk_level} Risk
                    </Badge>
                  </div>

                  {/* Quantitative Metrics */}
                  <div className="mt-4 pt-3 border-t border-border grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <span className="text-[11px] text-muted-foreground block">Predicted Activity</span>
                      <span className="text-sm font-mono font-bold text-foreground">
                        {item.predicted_crimes.toFixed(1)}
                      </span>
                      <span className="text-[10px] text-muted-foreground ml-1">incidents</span>
                    </div>

                    <div>
                      <span className="text-[11px] text-muted-foreground block">Risk Score</span>
                      <span className="text-sm font-mono font-bold text-foreground">
                        {item.risk_score.toFixed(3)}
                      </span>
                      <span className="text-[10px] text-muted-foreground ml-1">/ 1.0</span>
                    </div>
                  </div>

                  {/* Visual Risk Bar */}
                  <div className="mt-3">
                    <div className="w-full bg-secondary/80 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          item.risk_level === 'High'
                            ? 'bg-rose-500'
                            : item.risk_level === 'Medium'
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.max(5, item.risk_score * 100)}%` }}
                      />
                    </div>
                  </div>

                  {/* Confidence Footer */}
                  <div className="mt-3 pt-2 border-t border-border/60 flex items-center justify-between text-[11px] text-muted-foreground">
                    <span>Reliability Index</span>
                    <span className="font-mono text-emerald-400 font-semibold">
                      {(item.confidence_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

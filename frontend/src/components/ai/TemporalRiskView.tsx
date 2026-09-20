import { useState } from 'react';
import {
  Calendar,
  AlertTriangle,
  RefreshCw,
  Info,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { PredictionDisclaimerBanner } from '@/components/ai/PredictionDisclaimerBanner';
import { useTemporalRisk } from '@/hooks/usePredictions';

const CITIES = [
  'Delhi',
  'Mumbai',
  'Bangalore',
  'Hyderabad',
  'Kolkata',
  'Chennai',
  'Ahmedabad',
  'Pune',
  'Jaipur',
  'Lucknow',
  'Kanpur',
  'Nagpur',
  'Indore',
  'Thane',
  'Bhopal',
  'Visakhapatnam',
  'Patna',
  'Vadodara',
  'Ghaziabad',
  'Ludhiana',
  'Agra',
  'Nashik',
  'Faridabad',
  'Meerut',
  'Rajkot',
  'Kalyan',
  'Vasai',
  'Varanasi',
  'Srinagar',
];

export function TemporalRiskView() {
  const [selectedCity, setSelectedCity] = useState<string>('Delhi');

  const { data, isLoading, isError, error, refetch } = useTemporalRisk(selectedCity);

  // Combine historical and predicted points for the multi-series line chart
  const combinedChartData = (() => {
    if (!data) return [];
    const points: Array<{
      label: string;
      historical?: number;
      predicted?: number;
      lower_bound?: number;
      upper_bound?: number;
    }> = [];

    // Historical days (-7 to -1)
    if (data.historical_context && data.historical_context.length > 0) {
      data.historical_context.forEach((h) => {
        points.push({
          label: h.day_label,
          historical: h.crime_count,
        });
      });
    }

    // Bridge point linking historical and predicted
    if (points.length > 0 && data.forecast.length > 0) {
      const lastHist = points[points.length - 1];
      points.push({
        label: 'Current',
        historical: lastHist.historical,
        predicted: lastHist.historical,
        lower_bound: lastHist.historical,
        upper_bound: lastHist.historical,
      });
    }

    // Forecast days (+1 to +7)
    data.forecast.forEach((f) => {
      points.push({
        label: `Day +${f.day}`,
        predicted: f.predicted_crimes,
        lower_bound: f.lower_bound_95,
        upper_bound: f.upper_bound_95,
      });
    });

    return points;
  })();

  const avgPredicted =
    data && data.forecast.length > 0
      ? (
          data.forecast.reduce((acc, curr) => acc + curr.predicted_crimes, 0) /
          data.forecast.length
        ).toFixed(1)
      : '0.0';

  return (
    <div className="space-y-6">
      {/* Top Banner: Global Ethics Disclaimer */}
      <PredictionDisclaimerBanner customText={data?.disclaimer} />

      {/* Control Header */}
      <Card className="p-4 bg-card/60 backdrop-blur border border-border">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Calendar size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-foreground">7-Day Crime Activity Forecast</h2>
                <Badge variant="blue">Phase 3 GRU</Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Temporal sequential forecasting with empirical 95% prediction intervals
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* City Selector */}
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-muted-foreground">City:</span>
              <select
                value={selectedCity}
                onChange={(e) => setSelectedCity(e.target.value)}
                className="h-8 rounded-lg bg-secondary border border-border px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {CITIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
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

      {/* Scope Clarification Alert */}
      {data && (
        <div className="flex items-start gap-2.5 p-3 rounded-xl bg-secondary/60 border border-border text-xs text-muted-foreground">
          <Info size={16} className="text-blue-400 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <span className="font-semibold text-foreground">Model Scope:</span>{' '}
            {data.prediction_scope}.{' '}
            <span className="text-[11px] text-muted-foreground/80 block mt-0.5">
              Evaluates multivariate national indicators (13 features) over a 30-day lookback window while capturing query context for {selectedCity}.
            </span>
          </div>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <Card className="p-8 text-center animate-pulse space-y-4">
          <div className="h-6 bg-muted rounded w-1/4 mx-auto" />
          <div className="h-56 bg-muted rounded" />
        </Card>
      )}

      {/* Error State */}
      {isError && (
        <Card className="p-6 text-center text-red-400 space-y-2 border-red-500/30">
          <AlertTriangle size={24} className="mx-auto text-red-400" />
          <p className="text-sm font-semibold">Failed to load temporal forecast</p>
          <p className="text-xs text-muted-foreground">{(error as Error)?.message}</p>
        </Card>
      )}

      {/* Main Forecast Chart & Stats */}
      {data && (
        <div className="space-y-6">
          {/* Summary KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-3.5 rounded-xl bg-secondary/50 border border-border">
              <div className="text-[11px] font-medium text-muted-foreground">Forecast Horizon</div>
              <div className="text-base font-bold text-foreground mt-0.5">Next 7 Days</div>
            </div>
            <div className="p-3.5 rounded-xl bg-secondary/50 border border-border">
              <div className="text-[11px] font-medium text-muted-foreground">Avg Daily Projected</div>
              <div className="text-base font-bold text-blue-400 mt-0.5">{avgPredicted} Crimes</div>
            </div>
            <div className="p-3.5 rounded-xl bg-secondary/50 border border-border">
              <div className="text-[11px] font-medium text-muted-foreground">Uncertainty Bound</div>
              <div className="text-base font-bold text-foreground mt-0.5">95% Interval</div>
            </div>
            <div className="p-3.5 rounded-xl bg-secondary/50 border border-border">
              <div className="text-[11px] font-medium text-muted-foreground">Architecture</div>
              <div className="text-base font-bold text-emerald-400 mt-0.5">2-Layer GRU (Best)</div>
            </div>
          </div>

          {/* Combined Chronological Area Chart */}
          <Card className="p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
              <div>
                <h3 className="text-sm font-bold text-foreground">
                  Historical Incident Counts vs. 7-Day Predicted Forecast
                </h3>
                <p className="text-xs text-muted-foreground">
                  Solid blue indicates historical observation; purple/dashed indicates future GRU projection
                </p>
              </div>

              <div className="flex items-center gap-3 text-xs">
                <span className="flex items-center gap-1 text-sky-400 font-medium">
                  <span className="w-2.5 h-2.5 rounded-full bg-sky-400 inline-block" /> Historical
                </span>
                <span className="flex items-center gap-1 text-purple-400 font-medium">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-400 inline-block" /> Predicted Forecast
                </span>
              </div>
            </div>

            <div className="h-72 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={combinedChartData}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="historicalGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="predictedGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#a855f7" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#a855f7" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: '#64748b', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  {/* Historical Area */}
                  <Area
                    type="monotone"
                    dataKey="historical"
                    stroke="#38bdf8"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#historicalGrad)"
                    name="Historical Crimes"
                  />
                  {/* Predicted Area */}
                  <Area
                    type="monotone"
                    dataKey="predicted"
                    stroke="#a855f7"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    fillOpacity={1}
                    fill="url(#predictedGrad)"
                    name="Predicted Crimes"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Daily Breakdown Table */}
          <Card className="p-5 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Day-by-Day Forecast Breakdown & Prediction Intervals
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-3">
              {data.forecast.map((d) => (
                <div
                  key={d.day}
                  className="p-3 rounded-xl bg-secondary/40 border border-border flex flex-col justify-between"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-foreground">Day +{d.day}</span>
                    <Badge variant="blue">{(d.confidence_score * 100).toFixed(0)}%</Badge>
                  </div>

                  <div className="my-2">
                    <span className="text-[10px] text-muted-foreground block">Predicted Count</span>
                    <span className="text-lg font-mono font-bold text-purple-300">
                      {d.predicted_crimes.toFixed(2)}
                    </span>
                  </div>

                  <div className="pt-2 border-t border-border/60 text-[10px] text-muted-foreground">
                    <span>95% Bounds:</span>
                    <span className="font-mono block text-foreground font-medium">
                      [{d.lower_bound_95?.toFixed(2)} - {d.upper_bound_95?.toFixed(2)}]
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

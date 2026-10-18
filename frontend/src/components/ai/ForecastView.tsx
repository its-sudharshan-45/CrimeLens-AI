import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Info,
  RefreshCw,
  ShieldQuestion,
} from 'lucide-react';
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { PredictionDisclaimerBanner } from '@/components/ai/PredictionDisclaimerBanner';
import { useForecast, useScopes } from '@/hooks/useAI';
import type { ScopeType } from '@/types/ai';

interface PerHorizonRow {
  step: string;
  modelMAE: number | null;
  baselineMAE: number | null;
}

function metricRows(perHorizon: Record<string, unknown>): PerHorizonRow[] {
  const model = (perHorizon?.model ?? {}) as Record<string, { MAE?: number }>;
  const baseline = (perHorizon?.persistence_baseline ?? {}) as Record<string, { MAE?: number }>;
  return Object.keys(model)
    .filter((k) => k.startsWith('Day +'))
    .map((step) => ({
      step,
      modelMAE: typeof model[step]?.MAE === 'number' ? model[step].MAE : null,
      baselineMAE: typeof baseline[step]?.MAE === 'number' ? baseline[step].MAE : null,
    }));
}

export function ForecastView() {
  const [scopeType, setScopeType] = useState<ScopeType>('city');
  const [scopeValue, setScopeValue] = useState<string>('');

  const scopesQuery = useScopes(scopeType);
  const scopes = useMemo(() => scopesQuery.data?.scopes ?? [], [scopesQuery.data]);

  // Reset the selected value whenever the scope type (and its options) change.
  useEffect(() => {
    if (scopes.length === 0) {
      setScopeValue('');
      return;
    }
    setScopeValue((current) =>
      current && scopes.some((s) => s.display_name === current) ? current : scopes[0].display_name
    );
  }, [scopes]);

  const forecastQuery = useForecast(scopeValue ? { scope_type: scopeType, scope_value: scopeValue } : null);
  const data = forecastQuery.data;

  const chartData = useMemo(() => {
    if (!data) return [];
    const points: Array<{ label: string; historical?: number; predicted?: number; lower?: number; upper?: number }> = [];
    const history = data.historical.slice(-30);
    history.forEach((h) => points.push({ label: h.date.slice(5), historical: h.count }));
    if (history.length && data.forecast.length) {
      const last = history[history.length - 1];
      points.push({ label: 'now', historical: last.count, predicted: last.count, lower: last.count, upper: last.count });
    }
    data.forecast.forEach((f) => {
      points.push({
        label: f.date.slice(5),
        predicted: f.predicted_count,
        lower: f.lower_bound_95,
        upper: f.upper_bound_95,
      });
    });
    return points;
  }, [data]);

  const backtestData = useMemo(
    () =>
      (data?.actual_vs_predicted ?? []).map((p) => ({
        label: p.date.slice(5),
        actual: p.actual,
        predicted: p.predicted,
      })),
    [data]
  );

  const horizonRows = useMemo(() => metricRows(data?.per_horizon_metrics ?? {}), [data]);

  const modelMetrics = data?.test_metrics?.model;
  const baselineMetrics = data?.test_metrics?.persistence_baseline;
  const avgPredicted =
    data && data.forecast.length
      ? data.forecast.reduce((acc, f) => acc + f.predicted_count, 0) / data.forecast.length
      : 0;

  const isInitialLoading = scopesQuery.isLoading || (forecastQuery.isFetching && !data);
  const hasError = scopesQuery.isError || forecastQuery.isError;
  const errorMessage = (scopesQuery.error as Error | null)?.message ?? (forecastQuery.error as Error | null)?.message;

  return (
    <div className="space-y-6">
      <PredictionDisclaimerBanner customText={data?.disclaimer} />

      {/* Control header */}
      <Card className="p-4 bg-card/60 backdrop-blur border border-border">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Activity size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-foreground">7-Day Crime-Count Forecast</h2>
                <Badge variant="blue">GRU</Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Single deep-learning model · 30-day lookback · empirical 95% intervals
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-muted-foreground">Scope:</span>
              <select
                value={scopeType}
                onChange={(e) => setScopeType(e.target.value as ScopeType)}
                className="h-8 rounded-lg bg-secondary border border-border px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="city">City</option>
                <option value="crime_type">Crime Type</option>
              </select>
            </div>

            <select
              value={scopeValue}
              onChange={(e) => setScopeValue(e.target.value)}
              disabled={scopes.length === 0}
              className="h-8 max-w-[220px] rounded-lg bg-secondary border border-border px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {scopes.length === 0 && <option value="">No scopes available</option>}
              {scopes.map((s) => (
                <option key={s.key} value={s.display_name}>
                  {s.display_name}
                </option>
              ))}
            </select>

            <Button
              variant="outline"
              size="sm"
              onClick={() => forecastQuery.refetch()}
              disabled={forecastQuery.isFetching || !scopeValue}
              className="h-8 text-xs"
            >
              <RefreshCw size={12} className={`mr-1.5 ${forecastQuery.isFetching ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>
      </Card>

      {/* Loading */}
      {isInitialLoading && (
        <Card className="p-8 text-center animate-pulse space-y-4">
          <div className="h-6 bg-muted rounded w-1/4 mx-auto" />
          <div className="h-56 bg-muted rounded" />
        </Card>
      )}

      {/* Error */}
      {hasError && !isInitialLoading && (
        <Card className="p-6 text-center text-red-400 space-y-2 border-red-500/30">
          <AlertTriangle size={24} className="mx-auto text-red-400" />
          <p className="text-sm font-semibold">Failed to load forecast</p>
          <p className="text-xs text-muted-foreground">{errorMessage}</p>
        </Card>
      )}

      {data && (
        <div className="space-y-6">
          {/* Honest model card */}
          <div className="flex items-start gap-2.5 p-3 rounded-xl bg-secondary/60 border border-border text-xs text-muted-foreground">
            <Info size={16} className="text-blue-400 shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <span className="font-semibold text-foreground">Scope:</span>{' '}
              {data.scope_display_name} ({data.scope_type}). Forecast starts after the last observed date{' '}
              <span className="font-mono">{data.last_observed_date}</span>. The dataset is synthetic and its daily
              counts carry little temporal signal, so the GRU performs close to the naive persistence baseline — this
              is reported honestly below.
            </div>
          </div>

          {/* KPIs */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-3.5 rounded-xl bg-secondary/50 border border-border">
              <div className="text-[11px] font-medium text-muted-foreground">Avg Daily Projected</div>
              <div className="text-base font-bold text-blue-400 mt-0.5">{avgPredicted.toFixed(2)}</div>
            </div>
            <div className="p-3.5 rounded-xl bg-secondary/50 border border-border">
              <div className="text-[11px] font-medium text-muted-foreground">Test MAE (GRU)</div>
              <div className="text-base font-bold text-foreground mt-0.5">
                {modelMetrics ? modelMetrics.MAE.toFixed(3) : 'n/a'}
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-secondary/50 border border-border">
              <div className="text-[11px] font-medium text-muted-foreground">Test MAE (Persistence)</div>
              <div className="text-base font-bold text-foreground mt-0.5">
                {baselineMetrics ? baselineMetrics.MAE.toFixed(3) : 'n/a'}
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-secondary/50 border border-border">
              <div className="text-[11px] font-medium text-muted-foreground">Beats Baseline?</div>
              <div
                className={`text-base font-bold mt-0.5 ${
                  data.test_metrics?.model_beats_baseline_MAE ? 'text-emerald-400' : 'text-amber-400'
                }`}
              >
                {data.test_metrics?.model_beats_baseline_MAE ? 'Yes' : 'No (≈ tie)'}
              </div>
            </div>
          </div>

          {/* Forecast chart */}
          <Card className="p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
              <div>
                <h3 className="text-sm font-bold text-foreground">
                  Historical Counts vs. 7-Day Predicted Forecast
                </h3>
                <p className="text-xs text-muted-foreground">
                  Last 30 observed days plus the GRU forecast and its 95% prediction interval
                </p>
              </div>
              <div className="flex items-center gap-3 text-xs">
                <span className="flex items-center gap-1 text-sky-400 font-medium">
                  <span className="w-2.5 h-2.5 rounded-full bg-sky-400 inline-block" /> Historical
                </span>
                <span className="flex items-center gap-1 text-purple-400 font-medium">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-400 inline-block" /> Forecast
                </span>
              </div>
            </div>

            <div className="h-72 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Area type="monotone" dataKey="upper" stroke="none" fill="#a855f7" fillOpacity={0.12} />
                  <Area type="monotone" dataKey="lower" stroke="none" fill="#0f172a" fillOpacity={0.0} />
                  <Line type="monotone" dataKey="historical" stroke="#38bdf8" strokeWidth={2} dot={false} name="Historical" />
                  <Line
                    type="monotone"
                    dataKey="predicted"
                    stroke="#a855f7"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    dot={false}
                    name="Predicted"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Day-by-day forecast */}
          <Card className="p-5 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Day-by-Day Forecast &amp; 95% Prediction Intervals
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-3">
              {data.forecast.map((d) => (
                <div key={d.day} className="p-3 rounded-xl bg-secondary/40 border border-border flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-foreground">Day +{d.day}</span>
                    <span className="text-[10px] text-muted-foreground font-mono">{d.date.slice(5)}</span>
                  </div>
                  <div className="my-2">
                    <span className="text-[10px] text-muted-foreground block">Predicted Count</span>
                    <span className="text-lg font-mono font-bold text-purple-300">{d.predicted_count.toFixed(2)}</span>
                  </div>
                  <div className="pt-2 border-t border-border/60 text-[10px] text-muted-foreground">
                    <span>95% bounds</span>
                    <span className="font-mono block text-foreground font-medium">
                      [{d.lower_bound_95.toFixed(2)}, {d.upper_bound_95.toFixed(2)}]
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Held-out backtest */}
          {backtestData.length > 0 && (
            <Card className="p-5 space-y-4">
              <div>
                <h3 className="text-sm font-bold text-foreground">Held-out Backtest — Actual vs Predicted</h3>
                <p className="text-xs text-muted-foreground">
                  Rolling one-step-ahead predictions over the untouched 2024 test window ({backtestData.length} days)
                </p>
              </div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={backtestData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey="label" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        borderColor: '#334155',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                    <Bar dataKey="actual" fill="#38bdf8" fillOpacity={0.4} name="Actual" />
                    <Line type="monotone" dataKey="predicted" stroke="#f59e0b" strokeWidth={2} dot={false} name="Predicted" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          {/* Per-horizon error + honesty */}
          {horizonRows.length > 0 && (
            <Card className="p-5 space-y-4">
              <div className="flex items-center gap-2">
                <ShieldQuestion size={16} className="text-amber-400" />
                <h3 className="text-sm font-bold text-foreground">Per-Step Error vs. Persistence Baseline</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-muted-foreground text-left border-b border-border">
                      <th className="py-2 font-medium">Forecast step</th>
                      <th className="py-2 font-medium text-right">GRU MAE</th>
                      <th className="py-2 font-medium text-right">Persistence MAE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {horizonRows.map((r) => (
                      <tr key={r.step} className="border-b border-border/50">
                        <td className="py-1.5 text-foreground">{r.step}</td>
                        <td className="py-1.5 text-right font-mono text-purple-300">
                          {r.modelMAE === null ? 'n/a' : r.modelMAE.toFixed(3)}
                        </td>
                        <td className="py-1.5 text-right font-mono text-muted-foreground">
                          {r.baselineMAE === null ? 'n/a' : r.baselineMAE.toFixed(3)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                {String(
                  data.evaluation_summary?.honest_note ??
                    'Metrics are computed on the untouched held-out test split. No fabricated values are shown.'
                )}
              </p>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

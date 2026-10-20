import { useMemo, useState, type FormEvent } from 'react';
import {
  Activity,
  AlertTriangle,
  Brain,
  CalendarDays,
  Info,
  MapPin,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react';

import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Label } from '@/components/ui/Label';
import { SearchableSelect } from '@/components/ui/SearchableSelect';
import { useAIHealth, useLocations, useRiskPrediction } from '@/hooks/useAI';
import { formatDate } from '@/lib/utils';
import type { RiskCategory, RiskForecastDay } from '@/types/ai';

const categoryStyles: Record<
  RiskCategory,
  { color: string; badge: 'emerald' | 'amber' | 'red'; surface: string; label: string }
> = {
  Low: {
    color: '#10b981',
    badge: 'emerald',
    surface: 'border-emerald-500/25 bg-emerald-500/5',
    label: 'Low risk',
  },
  Medium: {
    color: '#f59e0b',
    badge: 'amber',
    surface: 'border-amber-500/25 bg-amber-500/5',
    label: 'Medium risk',
  },
  High: {
    color: '#ef4444',
    badge: 'red',
    surface: 'border-red-500/25 bg-red-500/5',
    label: 'High risk',
  },
};

function RiskGauge({ score, category }: { score: number; category: RiskCategory }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - Math.min(100, Math.max(0, score)) / 100);
  const tone = categoryStyles[category];

  return (
    <div
      className="relative mx-auto h-48 w-48"
      role="img"
      aria-label={`Relative crime risk ${score.toFixed(1)} percent, ${tone.label}`}
    >
      <svg viewBox="0 0 140 140" className="h-full w-full -rotate-90">
        <circle cx="70" cy="70" r={radius} fill="none" stroke="currentColor" strokeWidth="11" className="text-border" />
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke={tone.color}
          strokeWidth="11"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 500ms ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="text-4xl font-bold tracking-tight" style={{ color: tone.color }}>
          {score.toFixed(1)}%
        </span>
        <span className="mt-0.5 text-[11px] text-muted-foreground">relative risk index</span>
        <span className="mt-1 text-xs font-semibold" style={{ color: tone.color }}>
          {tone.label}
        </span>
      </div>
    </div>
  );
}

function MetricTile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-border bg-secondary/40 p-4">
      <p className="text-[11px] font-medium text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold text-foreground">{value}</p>
      {hint && <p className="mt-1 text-[11px] leading-snug text-muted-foreground">{hint}</p>}
    </div>
  );
}

function ForecastStrip({ days }: { days: RiskForecastDay[] }) {
  const max = Math.max(...days.map((day) => day.predicted_count), 1);

  return (
    <div className="grid grid-cols-7 gap-2">
      {days.map((day) => {
        const height = Math.max(6, (day.predicted_count / max) * 100);
        return (
          <div key={day.day} className="flex min-w-0 flex-col items-center">
            <div className="flex h-24 w-full items-end justify-center rounded-md bg-secondary/30 px-1.5 pb-1">
              <div
                className="w-full max-w-[26px] rounded-t bg-emerald-500/55"
                style={{ height: `${height}%` }}
                title={`${day.predicted_count.toFixed(2)} predicted incidents`}
              />
            </div>
            <span className="mt-1.5 font-mono text-[11px] font-semibold text-foreground">
              {day.predicted_count.toFixed(2)}
            </span>
            <span className="text-[10px] text-muted-foreground">
              {formatDate(day.date, { month: 'short', day: 'numeric' })}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function RiskPredictionPage() {
  const [selectedState, setSelectedState] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [validationError, setValidationError] = useState('');

  const locationsQuery = useLocations();
  const healthQuery = useAIHealth();
  const prediction = useRiskPrediction();

  const states = useMemo(() => locationsQuery.data?.states ?? [], [locationsQuery.data?.states]);
  const districts = useMemo(
    () => states.find((entry) => entry.state === selectedState)?.districts ?? [],
    [states, selectedState],
  );

  const stateOptions = useMemo(
    () =>
      states.map((entry) => ({
        value: entry.state,
        label: entry.state,
        description: `${entry.districts.length} districts`,
      })),
    [states],
  );

  const districtOptions = useMemo(
    () =>
      districts.map((entry) => ({
        value: entry.district,
        label: entry.district,
        description: entry.model_supported
          ? `Direct dataset coverage · ${entry.city} scope`
          : `Estimated from ${entry.city} scope`,
        keywords: entry.city,
      })),
    [districts],
  );

  const directDistrictCount = useMemo(
    () => districts.filter((entry) => entry.model_supported).length,
    [districts],
  );

  const selectedDistrictEntry = useMemo(
    () => districts.find((entry) => entry.district === selectedDistrict),
    [districts, selectedDistrict],
  );

  const handleStateChange = (value: string) => {
    setSelectedState(value);
    setSelectedDistrict('');
    setValidationError('');
    prediction.reset();
  };

  const handleDistrictChange = (value: string) => {
    setSelectedDistrict(value);
    setValidationError('');
    prediction.reset();
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!selectedState || !selectedDistrict) {
      setValidationError('Select both a state and a district before running the prediction.');
      return;
    }
    setValidationError('');
    prediction.mutate({ state: selectedState, district: selectedDistrict });
  };

  const result = prediction.data;
  const tone = result ? categoryStyles[result.risk_category] : null;
  const modelReady = healthQuery.data?.loaded === true;
  const errorMessage =
    prediction.error instanceof Error
      ? prediction.error.message
      : 'The prediction could not be generated. Please try again.';

  return (
    <div className="mx-auto max-w-5xl space-y-6 animate-fade-in">
      <header className="flex flex-col gap-4 border-b border-border pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">District Crime Risk Prediction</h1>
            <Badge variant="emerald">PyTorch GRU</Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Select a state and district to generate a deep-learning crime risk assessment from historical incident data.
          </p>
        </div>

        <div className="flex items-center gap-2 rounded-full border border-border bg-secondary/40 px-3 py-1.5 text-xs">
          <span
            className={`h-2 w-2 rounded-full ${modelReady ? 'bg-emerald-400' : 'bg-amber-400'}`}
            aria-hidden="true"
          />
          <span className="whitespace-nowrap text-muted-foreground">
            {healthQuery.isLoading ? 'Checking model…' : modelReady ? 'Model loaded' : 'Model unavailable'}
          </span>
        </div>
      </header>

      <Card className="p-5 sm:p-6">
        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          <div className="flex items-start gap-3">
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-2 text-emerald-400">
              <MapPin size={18} />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-foreground">Choose a jurisdiction</h2>
              <p className="text-xs text-muted-foreground">
                All 789 districts across 36 States and Union Territories are listed. Districts with a
                direct dataset scope use their own model; the rest show an estimate from a
                representative city scope.
              </p>
            </div>
          </div>

          {locationsQuery.isError && (
            <div className="flex flex-col gap-3 rounded-xl border border-red-500/25 bg-red-500/5 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-2.5">
                <AlertTriangle size={16} className="mt-0.5 shrink-0 text-red-400" />
                <div>
                  <p className="text-sm font-medium text-red-400">Could not load locations</p>
                  <p className="text-xs text-muted-foreground">
                    {(locationsQuery.error as Error | null)?.message ?? 'The location catalog is unavailable.'}
                  </p>
                </div>
              </div>
              <Button type="button" variant="outline" size="sm" onClick={() => locationsQuery.refetch()}>
                <RefreshCw size={13} /> Retry
              </Button>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="state-select" required>
                State / Union Territory
              </Label>
              <SearchableSelect
                id="state-select"
                value={selectedState}
                onChange={handleStateChange}
                options={stateOptions}
                placeholder={locationsQuery.isLoading ? 'Loading states…' : 'Search or select a state'}
                searchPlaceholder="Search states and UTs…"
                emptyMessage="No matching state or UT"
                disabled={locationsQuery.isLoading || states.length === 0}
              />
            </div>

            <div>
              <Label htmlFor="district-select" required>
                District
              </Label>
              <SearchableSelect
                id="district-select"
                value={selectedDistrict}
                onChange={handleDistrictChange}
                options={districtOptions}
                placeholder={selectedState ? 'Search or select a district' : 'Select a state first'}
                searchPlaceholder="Search districts…"
                emptyMessage="No matching district"
                disabled={!selectedState || districts.length === 0}
              />
            </div>
          </div>

          {selectedState && districts.length > 0 && (
            <p className="text-[11px] text-muted-foreground">
              {districts.length} districts in {selectedState}
              {directDistrictCount > 0
                ? ` · ${directDistrictCount} with direct dataset coverage`
                : ' · estimated from a representative dataset scope'}
            </p>
          )}

          {selectedDistrictEntry?.coverage === 'proxy' && (
            <div className="flex items-start gap-2 rounded-xl border border-amber-500/25 bg-amber-500/5 p-3">
              <Info size={14} className="mt-0.5 shrink-0 text-amber-400" />
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                <span className="font-medium text-foreground">{selectedDistrictEntry.district}</span> is
                not one of the dataset cities. The risk index will be estimated from the{' '}
                <span className="font-medium text-foreground">{selectedDistrictEntry.city}</span> model
                scope and labelled as a proxy estimate.
              </p>
            </div>
          )}

          {validationError && (
            <p className="flex items-center gap-1.5 text-xs text-red-400" role="alert">
              <AlertTriangle size={13} /> {validationError}
            </p>
          )}

          <div className="flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <Info size={13} className="shrink-0" />
              The prediction uses the actual trained model — no random or hard-coded values.
            </p>
            <Button type="submit" loading={prediction.isPending} disabled={locationsQuery.isLoading}>
              <Brain size={15} />
              {prediction.isPending ? 'Running model…' : 'Predict Crime Risk'}
            </Button>
          </div>
        </form>
      </Card>

      {prediction.isError && (
        <div className="flex items-start gap-3 rounded-xl border border-red-500/25 bg-red-500/5 p-4" role="alert">
          <AlertTriangle size={17} className="mt-0.5 shrink-0 text-red-400" />
          <div>
            <p className="text-sm font-semibold text-red-400">Prediction failed</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{errorMessage}</p>
          </div>
        </div>
      )}

      {!result && !prediction.isPending && !prediction.isError && (
        <Card className="p-10 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-border bg-secondary/50 text-muted-foreground">
            <Activity size={20} />
          </div>
          <h2 className="mt-4 text-sm font-semibold text-foreground">No prediction yet</h2>
          <p className="mx-auto mt-1 max-w-md text-xs leading-relaxed text-muted-foreground">
            Choose a state and district above, then run the prediction. The result will show the district risk
            category, predicted incident volume and a seven-day model forecast.
          </p>
        </Card>
      )}

      {prediction.isPending && !result && (
        <Card className="p-10 text-center">
          <div className="mx-auto h-9 w-9 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
          <p className="mt-4 text-sm font-medium text-foreground">Running the GRU model…</p>
          <p className="mt-1 text-xs text-muted-foreground">Loading the district history and generating a seven-day forecast.</p>
        </Card>
      )}

      {result && tone && (
        <>
          <Card className="overflow-hidden">
            <div className="flex flex-col gap-4 border-b border-border p-5 sm:flex-row sm:items-start sm:justify-between sm:p-6">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Prediction summary
                </p>
                <h2 className="mt-1 text-xl font-bold text-foreground">
                  {result.state} <span className="text-muted-foreground">/</span> {result.district}
                </h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  Dataset scope: <span className="font-medium text-foreground">{result.city}</span> ·
                  Coverage:{' '}
                  <span className="font-medium text-foreground">
                    {result.model_coverage === 'dataset' ? 'direct' : `proxy (${result.proxy_city})`}
                  </span>{' '}
                  · Model:{' '}
                  <span className="font-medium text-foreground">
                    {result.model_name} {result.model_version}
                  </span>
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2 self-start">
                <Badge variant={result.model_coverage === 'dataset' ? 'emerald' : 'amber'}>
                  {result.model_coverage === 'dataset' ? 'Direct dataset scope' : 'Proxy estimate'}
                </Badge>
                <Badge variant={tone.badge} dot className="text-sm">
                  {tone.label}
                </Badge>
              </div>
            </div>

            {result.model_coverage === 'proxy' && (
              <div className="flex items-start gap-2.5 border-b border-border bg-amber-500/5 px-5 py-3 sm:px-6">
                <AlertTriangle size={14} className="mt-0.5 shrink-0 text-amber-400" />
                <p className="text-[11px] leading-relaxed text-muted-foreground">
                  <span className="font-medium text-foreground">{result.district}</span> is not a
                  dataset city. This index is estimated from the{' '}
                  <span className="font-medium text-foreground">{result.city}</span> model scope and
                  should be read as a regional proxy, not a district-specific observation.
                </p>
              </div>
            )}

            <div className="grid items-center gap-6 p-5 sm:p-6 lg:grid-cols-[210px_1fr]">
              <RiskGauge score={result.risk_percentage} category={result.risk_category} />

              <div className="grid gap-3 sm:grid-cols-2">
                <MetricTile
                  label="Predicted daily incidents"
                  value={`${result.predicted_daily_average.toFixed(2)} / day`}
                  hint={`95% range ${result.prediction_interval_95.daily_lower.toFixed(2)}–${result.prediction_interval_95.daily_upper.toFixed(2)}`}
                />
                <MetricTile
                  label="Next 7 days"
                  value={`${result.predicted_7_day_total.toFixed(1)} incidents`}
                  hint={`Forecast from ${formatDate(result.last_observed_date)}`}
                />
                <MetricTile
                  label={result.model_coverage === 'proxy' ? 'Backing scope rank' : 'District rank'}
                  value={
                    result.district_rank
                      ? `#${result.district_rank} of ${result.district_count}`
                      : `— of ${result.district_count}`
                  }
                  hint={
                    result.model_coverage === 'proxy'
                      ? `Rank of the ${result.city} scope by predicted volume`
                      : 'By predicted daily incident volume'
                  }
                />
                <MetricTile
                  label="Historical data"
                  value={`${result.historical_incidents.toLocaleString()} incidents`}
                  hint={`${result.historical_daily_average.toFixed(2)} / day observed`}
                />
              </div>
            </div>

            <div className="border-t border-border p-5 sm:p-6">
              <div className="mb-4 flex items-center gap-2">
                <CalendarDays size={15} className="text-emerald-400" />
                <h3 className="text-sm font-semibold text-foreground">Seven-day model forecast</h3>
              </div>
              <ForecastStrip days={result.forecast} />
              <p className="mt-3 text-[11px] text-muted-foreground">
                Bars show the trained GRU's predicted incident count for each day. The 95% interval method is{' '}
                {result.uncertainty_method ?? 'the held-out empirical residual range'}.
              </p>
            </div>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <Card className="p-5">
              <div className="flex items-center gap-2">
                <TrendingUp size={15} className="text-emerald-400" />
                <h3 className="text-sm font-semibold text-foreground">How the risk score works</h3>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{result.risk_method}</p>
              <div className={`mt-4 rounded-xl border p-3.5 ${tone.surface}`}>
                <p className="text-[11px] text-muted-foreground">Risk band at the 95% prediction interval</p>
                <p className="mt-1 text-sm font-semibold" style={{ color: tone.color }}>
                  {result.risk_lower_bound.toFixed(1)}% – {result.risk_upper_bound.toFixed(1)}%
                </p>
              </div>
            </Card>

            <Card className="p-5">
              <div className="flex items-center gap-2">
                <ShieldCheck size={15} className="text-emerald-400" />
                <h3 className="text-sm font-semibold text-foreground">Model provenance</h3>
              </div>
              <dl className="mt-3 space-y-2 text-xs">
                <div className="flex items-center justify-between gap-4 border-b border-border/60 pb-2">
                  <dt className="text-muted-foreground">Architecture</dt>
                  <dd className="font-medium text-foreground">GRU (PyTorch)</dd>
                </div>
                <div className="flex items-center justify-between gap-4 border-b border-border/60 pb-2">
                  <dt className="text-muted-foreground">Held-out test MAE</dt>
                  <dd className="font-mono text-foreground">
                    {result.model_test_metrics.MAE?.toFixed(3) ?? 'n/a'} / day
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4 border-b border-border/60 pb-2">
                  <dt className="text-muted-foreground">Persistence baseline MAE</dt>
                  <dd className="font-mono text-foreground">
                    {result.persistence_test_metrics.MAE?.toFixed(3) ?? 'n/a'} / day
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted-foreground">Historical coverage</dt>
                  <dd className="text-right text-foreground">through {formatDate(result.last_observed_date)}</dd>
                </div>
              </dl>
            </Card>
          </div>

          <div className="flex items-start gap-2.5 rounded-xl border border-border bg-secondary/30 p-4 text-[11px] leading-relaxed text-muted-foreground">
            <Info size={14} className="mt-0.5 shrink-0 text-blue-400" />
            <p>{result.disclaimer}</p>
          </div>
        </>
      )}
    </div>
  );
}

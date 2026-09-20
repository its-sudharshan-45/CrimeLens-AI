import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Brain,
  Sparkles,
  TrendingUp,
  Info,
  RefreshCw,
  Sliders,
  Calendar,
  MapPin,
  FileText,
  User,
  Shield,
} from 'lucide-react';

import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Badge } from '@/components/ui/Badge';
import { StatCard } from '@/components/ui/StatCard';
import { Tabs } from '@/components/ui/Tabs';

import { useAIHealth, useModelMetadata, usePrediction, useForecast, useExplainability } from '@/hooks/useAI';
import { useAnalytics } from '@/hooks/useMLOps';

import { ModelHealthBadge } from '@/components/ai/ModelHealthBadge';
import { PredictionResultCard } from '@/components/ai/PredictionResultCard';
import { FeatureImportanceBar } from '@/components/ai/FeatureImportanceBar';
import { ForecastChart } from '@/components/ai/ForecastChart';
import { HotspotPredictionView } from '@/components/ai/HotspotPredictionView';
import { TemporalRiskView } from '@/components/ai/TemporalRiskView';
import { InvestigationAssistantPanel } from '@/components/ai/InvestigationAssistantPanel';
import { PredictionHistoryView } from '@/components/ai/PredictionHistoryView';
import { CrimePredictionRequest } from '@/types/ai';
import { formatCount, formatPercent } from '@/lib/utils';

// Validation Schema for Prediction Form
const predictionSchema = z.object({
  city: z.string().min(2, 'City name is required'),
  crime_description: z.string().min(5, 'Crime description must be at least 5 characters'),
  victim_age: z.coerce.number().min(0).max(120),
  victim_gender: z.string().min(1, 'Gender is required'),
  weapon_used: z.string().optional(),
  date_of_occurrence: z.string().min(1, 'Date of occurrence is required'),
  time_of_occurrence: z.string().min(1, 'Time of occurrence is required'),
  case_closed: z.string().optional(),
  crime_code: z.coerce.number().optional(),
});

type PredictionFormData = z.infer<typeof predictionSchema>;

export default function AIPredictionsPage() {
  const [activeTab, setActiveTab] = useState<'hotspots' | 'temporal' | 'leads' | 'history' | 'predict' | 'forecast' | 'models'>('hotspots');
  const [forecastHorizon, setForecastHorizon] = useState<7 | 30 | 90>(30);

  // Queries
  const { data: health, isLoading: isHealthLoading } = useAIHealth();
  const { data: metadata } = useModelMetadata();
  const { data: analytics, isLoading: isAnalyticsLoading } = useAnalytics();

  // Mutations
  const predictMutation = usePrediction();
  const forecastMutation = useForecast();
  const explainMutation = useExplainability();

  // Form setup
  const {
    register,
    handleSubmit,
    reset,
    getValues,
    formState: { errors },
  } = useForm<PredictionFormData>({
    resolver: zodResolver(predictionSchema),
    defaultValues: {
      city: 'Mumbai',
      crime_description: 'Theft of motor vehicle from residential parking area',
      victim_age: 34,
      victim_gender: 'M',
      weapon_used: 'None',
      date_of_occurrence: '01-08-2026 22:30',
      time_of_occurrence: '01-08-2026 22:30',
      case_closed: 'No',
      crime_code: 100,
    },
  });

  const onSubmitPredict = (data: PredictionFormData) => {
    const payload: CrimePredictionRequest = {
      ...data,
      date_reported: data.date_of_occurrence,
    };
    predictMutation.mutate(payload);
  };

  const handleRunXAI = () => {
    const formData = getValues();
    explainMutation.mutate({
      sample_record: {
        ...formData,
        date_reported: formData.date_of_occurrence,
      },
      target_class: predictMutation.data?.domain_code || 0,
    });
  };

  const handleRunForecast = (horizon: 7 | 30 | 90) => {
    setForecastHorizon(horizon);
    forecastMutation.mutate({ horizon });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-foreground">AI Pattern Prediction & Intelligence</h1>
            <Badge variant="emerald">PyTorch Core</Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Real-time crime domain classification, Captum feature attribution, and N-BEATS trend forecasting
          </p>
        </div>

        <ModelHealthBadge health={health} loading={isHealthLoading} />
      </div>

      {/* Overview Metric Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total AI Predictions"
          value={formatCount(analytics?.summary.total_predictions, isAnalyticsLoading)}
          icon={<Brain size={18} />}
          accent="emerald"
          loading={isAnalyticsLoading}
        />
        <StatCard
          label="Predictions Today"
          value={formatCount(analytics?.summary.predictions_today, isAnalyticsLoading)}
          icon={<Sparkles size={18} />}
          accent="blue"
          loading={isAnalyticsLoading}
        />
        <StatCard
          label="Avg Confidence"
          value={formatPercent(analytics?.summary.average_confidence, isAnalyticsLoading)}
          icon={<TrendingUp size={18} />}
          accent="purple"
          loading={isAnalyticsLoading}
        />
        <StatCard
          label="Active Model"
          value={metadata?.version ?? 'v1.0.0'}
          icon={<Shield size={18} />}
          accent="amber"
        />
      </div>

      {/* Module Navigation Tabs */}
      <Tabs
        tabs={[
          { id: 'hotspots', label: 'City Hotspots (CNN)' },
          { id: 'temporal', label: '7-Day Temporal Risk (GRU)' },
          { id: 'leads', label: 'Investigation Assistant' },
          { id: 'history', label: 'Prediction History' },
          { id: 'predict', label: 'Incident Classification' },
          { id: 'forecast', label: 'N-BEATS Trend' },
          { id: 'models', label: 'Model Metadata & Health' },
        ]}
        activeTab={activeTab}
        onChange={(id) => setActiveTab(id as any)}
      />

      {/* TAB: CITY HOTSPOTS (PHASE 4 CNN) */}
      {activeTab === 'hotspots' && <HotspotPredictionView />}

      {/* TAB: TEMPORAL RISK (PHASE 3 GRU) */}
      {activeTab === 'temporal' && <TemporalRiskView />}

      {/* TAB: INVESTIGATION ASSISTANT */}
      {activeTab === 'leads' && <InvestigationAssistantPanel />}

      {/* TAB: PREDICTION HISTORY */}
      {activeTab === 'history' && <PredictionHistoryView />}

      {/* TAB 1: PREDICT */}
      {activeTab === 'predict' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Prediction Input Form */}
          <Card className="lg:col-span-6 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div>
                <h3 className="text-sm font-bold text-foreground">Incident Feature Input</h3>
                <p className="text-xs text-muted-foreground">Input incident parameters for neural domain classification</p>
              </div>
              <Button type="button" variant="outline" size="sm" onClick={() => reset()}>
                <RefreshCw size={13} className="mr-1" /> Reset
              </Button>
            </div>

            <form onSubmit={handleSubmit(onSubmitPredict)} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="flex items-center gap-1 text-xs">
                    <MapPin size={12} className="text-emerald-400" /> City
                  </Label>
                  <Input {...register('city')} placeholder="e.g. Mumbai" error={errors.city?.message} />
                </div>

                <div className="space-y-1.5">
                  <Label className="flex items-center gap-1 text-xs">
                    <User size={12} className="text-blue-400" /> Victim Age
                  </Label>
                  <Input type="number" {...register('victim_age')} error={errors.victim_age?.message} />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="flex items-center gap-1 text-xs">
                  <FileText size={12} className="text-purple-400" /> Crime Description / Narrative
                </Label>
                <textarea
                  {...register('crime_description')}
                  rows={3}
                  className="w-full rounded-lg bg-input border border-border px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500/60"
                  placeholder="Describe the incident details, location type, or modus operandi..."
                />
                {errors.crime_description && (
                  <p className="text-[11px] text-red-400">{errors.crime_description.message}</p>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs">Victim Gender</Label>
                  <select
                    {...register('victim_gender')}
                    className="w-full rounded-lg bg-input border border-border px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
                  >
                    <option value="M">Male (M)</option>
                    <option value="F">Female (F)</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Weapon Used</Label>
                  <Input {...register('weapon_used')} placeholder="e.g. Knife, Firearm, None" />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="flex items-center gap-1 text-xs">
                    <Calendar size={12} className="text-amber-400" /> Date & Time of Occurrence
                  </Label>
                  <Input {...register('date_of_occurrence')} placeholder="01-08-2026 22:30" />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Crime Code</Label>
                  <Input type="number" {...register('crime_code')} />
                </div>
              </div>

              <Button
                type="submit"
                loading={predictMutation.isPending}
                className="w-full bg-emerald-500 hover:bg-emerald-600 text-black font-semibold mt-2"
              >
                <Brain size={16} className="mr-2" /> Classify Crime Domain (PyTorch)
              </Button>
            </form>
          </Card>

          {/* Results Column */}
          <div className="lg:col-span-6 space-y-6">
            {predictMutation.data ? (
              <>
                <PredictionResultCard
                  prediction={predictMutation.data}
                  onRunXAI={handleRunXAI}
                  isExplainLoading={explainMutation.isPending}
                />

                {/* XAI Attribution Section */}
                {explainMutation.data && (
                  <Card className="p-6 border-emerald-500/20 bg-emerald-500/5 space-y-4 animate-fade-in">
                    <div className="flex items-center justify-between border-b border-border/50 pb-3">
                      <div>
                        <h4 className="text-sm font-bold text-foreground">Captum Explainable AI (XAI)</h4>
                        <p className="text-xs text-muted-foreground">Integrated Gradients feature attribution</p>
                      </div>
                      <Badge variant="emerald">{explainMutation.data.method}</Badge>
                    </div>

                    <FeatureImportanceBar
                      features={explainMutation.data.top_contributing_features}
                      title="Top Feature Attributions"
                    />
                  </Card>
                )}
              </>
            ) : (
              <Card className="p-12 text-center flex flex-col items-center justify-center min-h-[400px]">
                <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-4 text-emerald-400">
                  <Brain size={32} />
                </div>
                <h3 className="text-base font-bold text-foreground">Awaiting Prediction Payload</h3>
                <p className="text-xs text-muted-foreground max-w-sm mt-1 mb-6">
                  Fill in the incident details on the left and click 'Classify Crime Domain' to trigger real-time neural inference.
                </p>
                <Button variant="outline" size="sm" onClick={() => handleSubmit(onSubmitPredict)()}>
                  <Sparkles size={14} className="mr-1.5" /> Run Sample Prediction
                </Button>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: FORECAST */}
      {activeTab === 'forecast' && (
        <Card className="p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
            <div>
              <h3 className="text-sm font-bold text-foreground">N-BEATS Multi-Horizon Sequence Forecaster</h3>
              <p className="text-xs text-muted-foreground">Predict future daily incident volume counts using deep neural time-series models</p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground font-medium">Horizon:</span>
              <div className="flex gap-1 bg-secondary/50 p-1 rounded-lg">
                {[7, 30, 90].map((h) => (
                  <button
                    key={h}
                    onClick={() => handleRunForecast(h as any)}
                    className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                      forecastHorizon === h
                        ? 'bg-emerald-500 text-black'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {h} Days
                  </button>
                ))}
              </div>
            </div>
          </div>

          {forecastMutation.data ? (
            <ForecastChart forecast={forecastMutation.data} />
          ) : (
            <div className="py-12 text-center flex flex-col items-center justify-center space-y-4">
              <TrendingUp size={40} className="text-emerald-400" />
              <div>
                <h4 className="text-sm font-bold text-foreground">Generate Crime Trend Forecast</h4>
                <p className="text-xs text-muted-foreground max-w-md mt-1">
                  Select a forecast horizon (7, 30, or 90 days) to run the N-BEATS deep learning forecaster.
                </p>
              </div>
              <Button onClick={() => handleRunForecast(30)} loading={forecastMutation.isPending}>
                <Sparkles size={14} className="mr-1.5" /> Run 30-Day Forecast
              </Button>
            </div>
          )}
        </Card>
      )}

      {/* TAB 3: MODEL METADATA */}
      {activeTab === 'models' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="p-6 space-y-4">
            <h3 className="text-sm font-bold text-foreground border-b border-border pb-3 flex items-center gap-2">
              <Sliders size={16} className="text-emerald-400" /> Active Model Architecture
            </h3>
            <div className="space-y-3 text-xs">
              <div className="flex justify-between py-1.5 border-b border-border/50">
                <span className="text-muted-foreground">Version</span>
                <span className="font-mono text-emerald-400 font-bold">{metadata?.version ?? 'v1.0.0'}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-border/50">
                <span className="text-muted-foreground">Framework</span>
                <span className="font-medium text-foreground">{metadata?.framework ?? 'PyTorch 2.2.0'}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-border/50">
                <span className="text-muted-foreground">Primary Classifier</span>
                <span className="font-medium text-foreground">{metadata?.flagship_model ?? 'FTTransformerClassifier'}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-border/50">
                <span className="text-muted-foreground">Forecaster Model</span>
                <span className="font-medium text-foreground">{metadata?.forecaster_model ?? 'NBEATSForecaster'}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-border/50">
                <span className="text-muted-foreground">Embedding Dimension</span>
                <span className="font-mono text-foreground font-semibold">{metadata?.embedding_dim ?? 64} dims</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-muted-foreground">Dataset MD5 Hash</span>
                <span className="font-mono text-muted-foreground truncate max-w-[180px]">
                  {metadata?.dataset_hash_md5 ?? 'N/A'}
                </span>
              </div>
            </div>
          </Card>

          <Card className="p-6 space-y-4">
            <h3 className="text-sm font-bold text-foreground border-b border-border pb-3 flex items-center gap-2">
              <Info size={16} className="text-blue-400" /> Subsystem Loading Matrix
            </h3>

            {health?.models_loaded && (
              <div className="space-y-2.5 text-xs">
                {Object.entries(health.models_loaded).map(([name, loaded]) => (
                  <div key={name} className="flex items-center justify-between p-2 rounded bg-secondary/40">
                    <span className="font-mono text-foreground">{name}</span>
                    <Badge variant={loaded ? 'emerald' : 'amber'}>
                      {loaded ? 'Loaded' : 'Offline'}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}

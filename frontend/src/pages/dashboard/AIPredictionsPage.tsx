import { useState } from 'react';
import { Brain, Sparkles, Activity, Shield } from 'lucide-react';

import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { StatCard } from '@/components/ui/StatCard';
import { Tabs } from '@/components/ui/Tabs';

import { useAIHealth, useModelMetadata } from '@/hooks/useAI';
import { usePredictionStats } from '@/hooks/usePredictions';

import { ModelHealthBadge } from '@/components/ai/ModelHealthBadge';
import { ForecastView } from '@/components/ai/ForecastView';
import { PredictionHistoryView } from '@/components/ai/PredictionHistoryView';
import { formatCount, formatMs } from '@/lib/utils';

type TabId = 'forecast' | 'history' | 'models';

export default function AIPredictionsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('forecast');

  const { data: health, isLoading: isHealthLoading } = useAIHealth();
  const { data: metadata, isLoading: isMetadataLoading } = useModelMetadata();
  const { data: stats, isLoading: isStatsLoading } = usePredictionStats();

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-foreground">AI Crime Forecasting</h1>
            <Badge variant="emerald">PyTorch GRU</Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            One deep-learning model: a 7-day crime-count forecaster with honest, held-out evaluation
          </p>
        </div>

        <ModelHealthBadge health={health} loading={isHealthLoading} />
      </div>

      {/* Overview Metric Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Forecasts"
          value={formatCount(stats?.total_predictions, isStatsLoading)}
          icon={<Brain size={18} />}
          accent="emerald"
          loading={isStatsLoading}
        />
        <StatCard
          label="Forecasts Today"
          value={formatCount(stats?.predictions_today, isStatsLoading)}
          icon={<Sparkles size={18} />}
          accent="blue"
          loading={isStatsLoading}
        />
        <StatCard
          label="Avg Inference Time"
          value={formatMs(stats?.avg_execution_time_ms, isStatsLoading)}
          icon={<Activity size={18} />}
          accent="purple"
          loading={isStatsLoading}
        />
        <StatCard
          label="Active Model"
          value={isMetadataLoading ? '…' : metadata?.version ?? 'forecast_v1'}
          icon={<Shield size={18} />}
          accent="amber"
          loading={isMetadataLoading}
        />
      </div>

      {/* Module Navigation Tabs */}
      <Tabs
        tabs={[
          { id: 'forecast', label: '7-Day Forecast (GRU)' },
          { id: 'history', label: 'Prediction History' },
          { id: 'models', label: 'Model Metadata & Health' },
        ]}
        activeTab={activeTab}
        onChange={(id) => setActiveTab(id as TabId)}
      />

      {activeTab === 'forecast' && <ForecastView />}
      {activeTab === 'history' && <PredictionHistoryView />}

      {activeTab === 'models' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="p-6 space-y-4">
            <h3 className="text-sm font-bold text-foreground border-b border-border pb-3 flex items-center gap-2">
              <Activity size={16} className="text-emerald-400" /> Active Model Architecture
            </h3>
            <div className="space-y-3 text-xs">
              <div className="flex justify-between py-1.5 border-b border-border/50">
                <span className="text-muted-foreground">Version</span>
                <span className="font-mono text-emerald-400 font-bold">{metadata?.version ?? 'forecast_v1'}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-border/50">
                <span className="text-muted-foreground">Model</span>
                <span className="font-medium text-foreground">{metadata?.primary_model ?? 'CrimeGRUForecaster'}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-border/50">
                <span className="text-muted-foreground">Framework</span>
                <span className="font-medium text-foreground">{metadata?.framework ?? 'PyTorch'}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-border/50">
                <span className="text-muted-foreground">Lookback / Horizon</span>
                <span className="font-medium text-foreground">
                  {metadata?.seq_len ?? 30} days / {metadata?.forecast_horizon ?? 7} days
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-border/50">
                <span className="text-muted-foreground">Input Features</span>
                <span className="font-mono text-foreground font-semibold">{metadata?.n_features ?? 6}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-border/50">
                <span className="text-muted-foreground">Forecast Scopes</span>
                <span className="font-mono text-foreground font-semibold">{metadata?.n_scopes ?? '—'}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-border/50">
                <span className="text-muted-foreground">Test MAE / Persistence MAE</span>
                <span className="font-mono text-foreground">
                  {metadata?.test_mae?.toFixed(3) ?? 'n/a'} / {metadata?.persistence_mae?.toFixed(3) ?? 'n/a'}
                </span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-muted-foreground">Dataset MD5</span>
                <span className="font-mono text-muted-foreground truncate max-w-[180px]">
                  {metadata?.dataset_hash_md5 ?? 'N/A'}
                </span>
              </div>
            </div>
          </Card>

          <Card className="p-6 space-y-4">
            <h3 className="text-sm font-bold text-foreground border-b border-border pb-3 flex items-center gap-2">
              <Shield size={16} className="text-blue-400" /> Subsystem Loading
            </h3>
            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between p-2 rounded bg-secondary/40">
                <span className="font-mono text-foreground">CrimeGRUForecaster</span>
                <Badge variant={health?.loaded ? 'emerald' : 'amber'}>
                  {health?.loaded ? 'Loaded' : 'Offline'}
                </Badge>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-secondary/40">
                <span className="text-muted-foreground">Device</span>
                <span className="font-mono text-foreground">{health?.device ?? 'cpu'}</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-secondary/40">
                <span className="text-muted-foreground">Scopes served</span>
                <span className="font-mono text-foreground">{health?.n_scopes ?? 0}</span>
              </div>
            </div>
            {health?.error && <p className="text-[11px] text-amber-400 leading-relaxed">{health.error}</p>}
          </Card>
        </div>
      )}
    </div>
  );
}

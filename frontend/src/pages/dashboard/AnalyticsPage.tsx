import {
  BarChart3,
  TrendingUp,
  Activity,
  Cpu,
  Server,
  Database,
  Clock,
  Zap,
} from 'lucide-react';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { StatCard } from '@/components/ui/StatCard';
import { Badge } from '@/components/ui/Badge';

import {
  useAnalytics,
  useMLOpsModels,
  useDriftStatus,
  useDriftReport,
  useSystemStatus,
} from '@/hooks/useMLOps';

import { AreaChartWidget } from '@/components/charts/AreaChartWidget';
import { DonutChartWidget } from '@/components/charts/DonutChartWidget';
import { DriftGauge } from '@/components/ai/DriftGauge';
import { ModelVersionCard } from '@/components/ai/ModelVersionCard';
import { formatUptime } from '@/types/ai';
import { formatCount, formatMs, formatPercent } from '@/lib/utils';

export default function AnalyticsPage() {
  const { data: analytics, isLoading: isAnalyticsLoading } = useAnalytics();
  const { data: modelsData } = useMLOpsModels();
  const { data: drift } = useDriftStatus();
  const { data: driftReport } = useDriftReport();
  const { data: system } = useSystemStatus();

  // Prepare chart data
  const distData = analytics?.prediction_distribution
    ? Object.entries(analytics.prediction_distribution).map(([name, value]) => ({ name, value }))
    : [];

  const trendData = analytics?.daily_prediction_trend
    ? analytics.daily_prediction_trend.map((d: any) => ({
        date: d.date || d.day || 'N/A',
        count: d.count || d.total || 0,
      }))
    : [];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Top Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-foreground">Advanced Analytics & Enterprise MLOps</h1>
            <Badge variant="emerald">Live Telemetry</Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Production model telemetry, distribution drift, prediction analytics, and hardware health
          </p>
        </div>
      </div>

      {/* SECTION 1: PREDICTION ANALYTICS */}
      <section className="space-y-4">
        <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <BarChart3 size={16} className="text-emerald-400" /> 1. Real-Time Inference Telemetry
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Total Predictions"
            value={formatCount(analytics?.summary.total_predictions, isAnalyticsLoading)}
            icon={<Zap size={18} />}
            accent="emerald"
            loading={isAnalyticsLoading}
          />
          <StatCard
            label="Predictions Today"
            value={formatCount(analytics?.summary.predictions_today, isAnalyticsLoading)}
            icon={<TrendingUp size={18} />}
            accent="blue"
            loading={isAnalyticsLoading}
          />
          <StatCard
            label="Avg. Confidence"
            value={formatPercent(analytics?.summary.average_confidence, isAnalyticsLoading)}
            icon={<Activity size={18} />}
            accent="purple"
            loading={isAnalyticsLoading}
          />
          <StatCard
            label="Avg. Latency"
            value={formatMs(analytics?.summary.average_inference_latency_ms, isAnalyticsLoading)}
            icon={<Clock size={18} />}
            accent="amber"
            loading={isAnalyticsLoading}
          />
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <Card className="lg:col-span-8 p-5">
            <CardHeader className="p-0 mb-4">
              <CardTitle className="text-sm font-bold">Daily Prediction Volume Trend</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <AreaChartWidget data={trendData} xKey="date" areaKey="count" name="Daily Predictions" height={240} />
            </CardContent>
          </Card>

          <Card className="lg:col-span-4 p-5">
            <CardHeader className="p-0 mb-4">
              <CardTitle className="text-sm font-bold">Crime Domain Distribution</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <DonutChartWidget data={distData} height={240} />
            </CardContent>
          </Card>
        </div>
      </section>

      {/* SECTION 2: DRIFT MONITORING */}
      <section className="space-y-4">
        <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Activity size={16} className="text-amber-400" /> 2. Live Model Drift Monitoring
        </h2>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-6">
            <DriftGauge drift={drift} />
          </div>

          <Card className="lg:col-span-6 p-5 space-y-3">
            <h3 className="text-sm font-bold text-foreground border-b border-border pb-2">
              Drift Analysis & Recommendations
            </h3>
            {driftReport ? (
              <div className="space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Drift Level:</span>
                  <Badge variant={driftReport.drift_level === 'LOW' ? 'emerald' : 'amber'}>
                    {driftReport.drift_level}
                  </Badge>
                </div>
                <div className="space-y-1">
                  <span className="text-muted-foreground block font-medium">Recommendation:</span>
                  <p className="p-3 rounded-lg bg-secondary/50 text-foreground font-mono text-[11px] leading-relaxed">
                    {driftReport.recommendation}
                  </p>
                </div>
                {driftReport.affected_features.length > 0 && (
                  <div>
                    <span className="text-muted-foreground block mb-1 font-medium">Affected Input Features:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {driftReport.affected_features.map((f) => (
                        <span key={f} className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">Loading drift recommendation report...</p>
            )}
          </Card>
        </div>
      </section>

      {/* SECTION 3: MODEL REGISTRY */}
      <section className="space-y-4">
        <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Cpu size={16} className="text-blue-400" /> 3. Model Registry & Version Tracking
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {modelsData?.models ? (
            modelsData.models.map((model) => (
              <ModelVersionCard
                key={model.version}
                model={model}
                isCurrent={model.version === system?.active_version}
              />
            ))
          ) : (
            <p className="text-xs text-muted-foreground col-span-3">Loading registered model versions...</p>
          )}
        </div>
      </section>

      {/* SECTION 4: SYSTEM & HARDWARE STATUS */}
      <section className="space-y-4">
        <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Server size={16} className="text-purple-400" /> 4. Production System Health & Infrastructure
        </h2>

        {system && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4 space-y-1">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>API Gateway</span>
                <Server size={14} className="text-emerald-400" />
              </div>
              <p className="text-lg font-bold text-foreground capitalize">{system.api_status}</p>
              <p className="text-[10px] text-muted-foreground font-mono">Uptime: {formatUptime(system.uptime_seconds)}</p>
            </Card>

            <Card className="p-4 space-y-1">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Database (PostgreSQL)</span>
                <Database size={14} className="text-emerald-400" />
              </div>
              <p className="text-lg font-bold text-foreground capitalize">{system.database_status}</p>
              <p className="text-[10px] text-muted-foreground truncate">{system.database_detail}</p>
            </Card>

            <Card className="p-4 space-y-1">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Supabase Sync</span>
                <Zap size={14} className="text-emerald-400" />
              </div>
              <p className="text-lg font-bold text-foreground capitalize">{system.supabase_status}</p>
              <p className="text-[10px] text-muted-foreground truncate">{system.supabase_detail}</p>
            </Card>

            <Card className="p-4 space-y-1">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Model Registry</span>
                <Cpu size={14} className="text-emerald-400" />
              </div>
              <p className="text-lg font-bold text-foreground capitalize">{system.registry_status}</p>
              <p className="text-[10px] text-muted-foreground truncate">{system.registry_detail}</p>
            </Card>
          </div>
        )}
      </section>
    </div>
  );
}

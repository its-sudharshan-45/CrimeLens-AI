import { AreaChartWidget } from '@/components/charts/AreaChartWidget';
import { Badge } from '@/components/ui/Badge';
import { ForecastResponse } from '@/types/ai';

interface ForecastChartProps {
  forecast?: ForecastResponse;
}

export function ForecastChart({ forecast }: ForecastChartProps) {
  if (!forecast) return null;

  const chartData = forecast.forecast_dates.map((date, idx) => ({
    date: date.split('T')[0],
    incidents: forecast.predicted_counts[idx],
  }));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            {forecast.horizon}-Day Projected Crime Incident Trend
          </h3>
          <p className="text-xs text-muted-foreground">
            Powered by PyTorch N-BEATS Forecaster ({forecast.model_version})
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <Badge variant="emerald">
            Projected Total: {forecast.total_projected_incidents} Incidents
          </Badge>
          <span className="font-mono text-muted-foreground">{forecast.execution_time_ms} ms</span>
        </div>
      </div>

      <AreaChartWidget
        data={chartData}
        xKey="date"
        areaKey="incidents"
        name="Projected Incidents"
        color="#3b82f6"
        height={280}
      />
    </div>
  );
}

import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';
import { ChartTooltip } from './ChartTooltip';

interface DonutChartWidgetProps {
  data: Array<{ name: string; value: number }>;
  height?: number;
  colors?: string[];
}

const DEFAULT_COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4'];

export function DonutChartWidget({
  data,
  height = 240,
  colors = DEFAULT_COLORS,
}: DonutChartWidgetProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-xs text-muted-foreground" style={{ height }}>
        No distribution data
      </div>
    );
  }

  const total = data.reduce((acc, cur) => acc + cur.value, 0);

  return (
    <div className="relative" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={85}
            paddingAngle={3}
            dataKey="value"
          >
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={colors[index % colors.length]} stroke="hsl(var(--card))" strokeWidth={2} />
            ))}
          </Pie>
          <Tooltip content={<ChartTooltip />} />
        </PieChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <span className="text-2xl font-bold text-foreground font-mono">{total}</span>
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Total</span>
      </div>
    </div>
  );
}

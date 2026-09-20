import { ShieldAlert, ShieldCheck, Lock, UserX, KeyRound, AlertTriangle } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { StatCard } from '@/components/ui/StatCard';
import { Badge } from '@/components/ui/Badge';
import { useSecurityDashboard } from '@/hooks/useSystem';

export default function SecurityDashboardPage() {
  const { data } = useSecurityDashboard();
  const metrics = data?.metrics;
  const alerts = data?.alerts ?? [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-foreground">Executive Security Dashboard</h1>
            <Badge variant="emerald">Threat Detection Active</Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Real-time monitoring of authentication events, failed access, session security, and unauthorized activity
          </p>
        </div>
      </div>

      {/* Primary Security Stat Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard
          label="Successful Logins (24h)"
          value={metrics?.successful_logins_24h ?? 0}
          icon={<ShieldCheck size={18} />}
          accent="emerald"
        />
        <StatCard
          label="Failed Logins (24h)"
          value={metrics?.failed_login_attempts_24h ?? 0}
          icon={<ShieldAlert size={18} />}
          accent="red"
        />
        <StatCard
          label="Active Sessions"
          value={metrics?.active_sessions_count ?? 0}
          icon={<Lock size={18} />}
          accent="blue"
        />
        <StatCard
          label="Locked Accounts"
          value={metrics?.locked_accounts_count ?? 0}
          icon={<UserX size={18} />}
          accent="amber"
        />
      </div>

      {/* Secondary Threat Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Password Resets (24h)', value: metrics?.password_reset_requests_24h ?? 0, icon: KeyRound, color: 'text-purple-400' },
          { label: 'Unauthorized Access (24h)', value: metrics?.unauthorized_access_attempts_24h ?? 0, icon: AlertTriangle, color: 'text-red-400' },
          { label: 'API Auth Failures (24h)', value: metrics?.api_auth_failures_24h ?? 0, icon: ShieldAlert, color: 'text-amber-400' },
          { label: 'Suspicious Incidents', value: metrics?.suspicious_activities_count ?? 0, icon: Lock, color: 'text-cyan-400' },
        ].map((item) => (
          <Card key={item.label} className="p-4 flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-secondary text-foreground">
              <item.icon size={18} className={item.color} />
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground uppercase font-semibold">{item.label}</p>
              <p className="text-xl font-bold font-mono text-foreground mt-0.5">{item.value}</p>
            </div>
          </Card>
        ))}
      </div>

      {/* Threat Alert Table */}
      <Card className="overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
            <ShieldAlert size={16} className="text-red-400" /> Active Security Alerts & Threat Incidents
          </h3>
          <Badge variant="red">{alerts.length} Flagged</Badge>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                {['Timestamp', 'Severity', 'Threat Title', 'Description', 'Source IP', 'Location', 'Target User', 'Status'].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {alerts.map((alt) => (
                <tr key={alt.id} className="border-b border-border/50 hover:bg-secondary/20">
                  <td className="px-4 py-3 font-mono text-muted-foreground whitespace-nowrap">{alt.timestamp}</td>
                  <td className="px-4 py-3">
                    <Badge variant={alt.severity === 'HIGH' || alt.severity === 'CRITICAL' ? 'red' : 'amber'}>
                      {alt.severity}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 font-semibold text-foreground">{alt.title}</td>
                  <td className="px-4 py-3 text-muted-foreground max-w-xs">{alt.description}</td>
                  <td className="px-4 py-3 font-mono text-foreground">{alt.source_ip}</td>
                  <td className="px-4 py-3 text-muted-foreground">{alt.location}</td>
                  <td className="px-4 py-3 font-mono text-muted-foreground">{alt.user_email}</td>
                  <td className="px-4 py-3">
                    <Badge variant="default">{alt.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useCrimeReports } from '@/hooks/useCrimeReports';
import { useInvestigations } from '@/hooks/useInvestigations';
import { useSystemHealth } from '@/hooks/useSystem';
import { StatCard } from '@/components/ui/StatCard';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { CrimeStatusBadge, PriorityBadge, InvestigationStatusBadge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  FileText, Search, Plus, ArrowRight, Brain, Shield, Activity,
} from 'lucide-react';

function greet(name: string) {
  const h = new Date().getHours();
  const salutation = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
  return `${salutation}, ${name?.split(' ')[0] || 'Officer'}.`;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const { data: reportsData, isLoading: reportsLoading } = useCrimeReports({ page: 1, page_size: 5 });
  const { data: investigationsData, isLoading: invLoading } = useInvestigations({ page: 1, page_size: 5 });
  const { data: systemHealth } = useSystemHealth({ live: false });

  const totalReports = reportsData?.total ?? 0;
  const totalInvestigations = investigationsData?.total ?? 0;

  const recentReports = (reportsData?.items ?? []).slice(0, 5);
  const recentInvestigations = (investigationsData?.items ?? []).slice(0, 5);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Executive Welcome & Primary Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-foreground">{greet(user?.full_name ?? '')}</h1>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Jurisdictional intelligence executive summary and active case dashboard
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/dashboard/reports')}
            className="flex items-center gap-2 h-9 px-4 bg-emerald-500 hover:bg-emerald-600 text-black text-xs font-semibold rounded-lg transition-all duration-200 shadow-md shadow-emerald-500/10"
          >
            <Plus size={14} />
            New Report
          </button>
          <button
            onClick={() => navigate('/dashboard/ai')}
            className="flex items-center gap-2 h-9 px-4 bg-secondary hover:bg-secondary/80 text-foreground border border-border text-xs font-semibold rounded-lg transition-all duration-200"
          >
            <Brain size={14} className="text-emerald-400" />
            AI Prediction
          </button>
        </div>
      </div>

      {/* Core Executive KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Crime Incidents"
          value={reportsLoading ? '—' : totalReports.toLocaleString()}
          icon={<FileText size={18} />}
          accent="emerald"
          loading={reportsLoading}
        />
        <StatCard
          label="Active Investigations"
          value={invLoading ? '—' : totalInvestigations.toLocaleString()}
          icon={<Search size={18} />}
          accent="amber"
          loading={invLoading}
        />
        <StatCard
          label="System Health"
          value={systemHealth?.overall_status ?? 'HEALTHY'}
          icon={<Activity size={18} />}
          accent="blue"
        />
        <StatCard
          label="AI Model Status"
          value="v1.0 Ready"
          icon={<Shield size={18} />}
          accent="emerald"
        />
      </div>

      {/* Split High-Priority Operational Feeds */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Crime Reports */}
        <Card className="overflow-hidden border border-border">
          <CardHeader className="border-b border-border bg-secondary/20 p-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <FileText size={16} className="text-emerald-400" /> Recent Crime Reports
              </CardTitle>
              <button
                onClick={() => navigate('/dashboard/reports')}
                className="flex items-center gap-1 text-xs font-semibold text-emerald-400 hover:underline"
              >
                View module <ArrowRight size={12} />
              </button>
            </div>
          </CardHeader>

          <div className="divide-y divide-border/50">
            {reportsLoading
              ? Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="p-4 flex gap-4">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-4 flex-1" />
                    <Skeleton className="h-4 w-16" />
                  </div>
                ))
              : recentReports.length === 0 ? (
                  <div className="p-8 text-center text-xs text-muted-foreground">No recent crime reports.</div>
                ) : (
                  recentReports.map((r) => (
                    <div
                      key={r.id}
                      onClick={() => navigate('/dashboard/reports')}
                      className="p-3.5 flex items-center justify-between hover:bg-secondary/20 transition-colors cursor-pointer"
                    >
                      <div className="space-y-0.5 min-w-0 flex-1 pr-3">
                        <div className="text-xs font-bold text-foreground truncate">{r.title}</div>
                        <div className="text-[11px] font-mono text-muted-foreground flex items-center gap-2">
                          <span>{r.crime_number}</span>
                          {r.location?.city && (
                            <>
                              <span>·</span>
                              <span>{r.location.city}</span>
                            </>
                          )}
                        </div>
                      </div>
                      <CrimeStatusBadge status={r.status} />
                    </div>
                  ))
                )}
          </div>
        </Card>

        {/* Active Cases Under Investigation */}
        <Card className="overflow-hidden border border-border">
          <CardHeader className="border-b border-border bg-secondary/20 p-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <Search size={16} className="text-amber-400" /> Active Cases Under Investigation
              </CardTitle>
              <button
                onClick={() => navigate('/dashboard/investigations')}
                className="flex items-center gap-1 text-xs font-semibold text-emerald-400 hover:underline"
              >
                View module <ArrowRight size={12} />
              </button>
            </div>
          </CardHeader>

          <div className="divide-y divide-border/50">
            {invLoading
              ? Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="p-4 flex gap-4">
                    <Skeleton className="h-4 flex-1" />
                    <Skeleton className="h-4 w-20" />
                  </div>
                ))
              : recentInvestigations.length === 0 ? (
                  <div className="p-8 text-center text-xs text-muted-foreground">No active cases under investigation.</div>
                ) : (
                  recentInvestigations.map((inv) => (
                    <div
                      key={inv.id}
                      onClick={() => navigate('/dashboard/investigations')}
                      className="p-3.5 flex items-center justify-between hover:bg-secondary/20 transition-colors cursor-pointer"
                    >
                      <div className="space-y-0.5 min-w-0 flex-1 pr-3">
                        <div className="text-xs font-bold text-foreground truncate">
                          {inv.report?.title ?? inv.report?.crime_number ?? 'Investigation Case'}
                        </div>
                        <div className="text-[11px] font-mono text-muted-foreground">
                          Logged: {new Date(inv.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <InvestigationStatusBadge status={inv.status} />
                        <PriorityBadge priority={inv.priority} />
                      </div>
                    </div>
                  ))
                )}
          </div>
        </Card>
      </div>
    </div>
  );
}

import { Link } from 'react-router-dom';
import { ArrowRight, ChevronDown, Activity, Target, FileSearch, Brain } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

const stats = [
  { value: '2.4M+', label: 'Crime Reports Analyzed', icon: FileSearch, color: 'text-emerald-400' },
  { value: '94.7%', label: 'Prediction Accuracy', icon: Target, color: 'text-emerald-400' },
  { value: '18K+', label: 'Active Investigations', icon: Activity, color: 'text-amber-400' },
  { value: '6.1M+', label: 'AI Insights Generated', icon: Brain, color: 'text-emerald-400' },
];

// CSS-based dashboard mockup panel
function DashboardMockup() {
  return (
    <div className="relative w-full max-w-xl mx-auto">
      {/* Outer glow */}
      <div className="absolute inset-0 rounded-2xl bg-emerald-500/5 blur-3xl" />

      {/* Main panel */}
      <div className="relative rounded-2xl border border-white/8 bg-charcoal-900/90 shadow-card-lg overflow-hidden">
        {/* Top bar */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5 bg-charcoal-950/60">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
          </div>
          <div className="flex-1 mx-4 h-5 bg-white/5 rounded-md flex items-center px-2">
            <span className="text-[10px] text-muted-foreground font-mono">crimelens.ai/dashboard</span>
          </div>
        </div>

        <div className="p-4 space-y-3">
          {/* Header row */}
          <div className="flex items-center justify-between">
            <div>
              <div className="h-3 w-32 bg-white/10 rounded" />
              <div className="h-2 w-20 bg-white/5 rounded mt-1.5" />
            </div>
            <div className="h-7 w-20 bg-emerald-500/20 rounded-lg border border-emerald-500/30 flex items-center justify-center">
              <span className="text-[10px] text-emerald-400 font-medium">Live Feed</span>
            </div>
          </div>

          {/* Chart area */}
          <div className="h-28 bg-white/3 rounded-lg border border-white/5 p-3 flex items-end gap-1.5">
            {[35, 55, 42, 68, 52, 78, 63, 85, 71, 90, 76, 88].map((h, i) => (
              <div
                key={i}
                className="flex-1 rounded-sm transition-all"
                style={{
                  height: `${h}%`,
                  background: i >= 9
                    ? 'rgba(16, 185, 129, 0.7)'
                    : 'rgba(16, 185, 129, 0.2)',
                }}
              />
            ))}
          </div>

          {/* Stat row */}
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: 'Hotspots', val: '24', color: 'text-emerald-400' },
              { label: 'Risk Score', val: 'HIGH', color: 'text-amber-400' },
              { label: 'Alerts', val: '7', color: 'text-red-400' },
            ].map((s) => (
              <div key={s.label} className="bg-white/3 rounded-lg p-2.5 border border-white/5">
                <p className={`text-sm font-bold ${s.color}`}>{s.val}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>

          {/* List items */}
          <div className="space-y-1.5">
            {[
              { type: 'Theft', loc: 'Downtown', risk: 'High', color: 'bg-red-500' },
              { type: 'Assault', loc: 'North District', risk: 'Medium', color: 'bg-amber-500' },
              { type: 'Burglary', loc: 'Harbor Area', risk: 'Low', color: 'bg-emerald-500' },
            ].map((item) => (
              <div
                key={item.type}
                className="flex items-center gap-3 p-2 bg-white/3 rounded-lg border border-white/5"
              >
                <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${item.color}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] text-foreground/80 font-medium">{item.type}</span>
                    <span className="text-[10px] text-muted-foreground">{item.loc}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function HeroSection() {
  const scrollToFeatures = () => {
    document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section className="relative min-h-screen flex items-center pt-16 overflow-hidden bg-grid">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-emerald-950/10 via-transparent to-transparent pointer-events-none" />
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-emerald-500/3 rounded-full blur-3xl pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left: Content */}
          <div className="animate-slide-up">
            <div className="mb-6">
              <Badge variant="emerald">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                AI-Powered Law Enforcement Platform
              </Badge>
            </div>

            <h1 className="heading-xl text-foreground mb-6 leading-[1.1]">
              AI-Powered Crime{' '}
              <span className="text-emerald-gradient">Prediction</span>{' '}
              &amp; Investigation Platform
            </h1>

            <p className="text-lg text-muted-foreground leading-relaxed mb-10 max-w-xl">
              CrimeLens AI empowers law enforcement agencies with advanced machine learning models,
              real-time crime pattern analysis, and intelligent investigation support — enabling
              faster, data-driven decisions to protect communities.
            </p>

            <div className="flex flex-col sm:flex-row gap-3 mb-14">
              <Link to="/signup">
                <Button variant="primary" size="lg" className="gap-2 w-full sm:w-auto" id="hero-get-started-btn">
                  Get Started
                  <ArrowRight size={16} />
                </Button>
              </Link>
              <button
                onClick={scrollToFeatures}
                className="inline-flex items-center justify-center gap-2 h-11 px-6 text-sm font-medium text-muted-foreground hover:text-foreground border border-border hover:border-border/80 rounded-lg transition-all duration-150"
                id="hero-learn-more-btn"
              >
                Learn More
                <ChevronDown size={16} />
              </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-3">
              {stats.map((stat) => (
                <div key={stat.label} className="stat-card">
                  <div className="flex items-center gap-2 mb-1.5">
                    <stat.icon size={14} className={stat.color} />
                    <span className={`text-xl font-bold ${stat.color}`}>{stat.value}</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-snug">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Dashboard Mockup */}
          <div className="animate-fade-in hidden lg:block">
            <DashboardMockup />
          </div>
        </div>
      </div>
    </section>
  );
}

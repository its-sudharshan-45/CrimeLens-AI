import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

// Animated bar chart values cycling to simulate live data
const chartValues = [38, 55, 44, 68, 52, 79, 63, 84, 71, 91, 77, 88];

function DashboardPreview() {
  const [activeBars, setActiveBars] = useState(9);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setTick((t) => t + 1);
      setActiveBars((prev) => (prev >= chartValues.length ? 3 : prev + 1));
    }, 1600);
    return () => clearInterval(interval);
  }, []);

  const liveItems = [
    { type: 'Theft', loc: 'Downtown', risk: 'High', color: 'bg-red-500', dot: 'text-red-400' },
    { type: 'Assault', loc: 'North District', risk: 'Medium', color: 'bg-amber-500', dot: 'text-amber-400' },
    { type: 'Burglary', loc: 'Harbor Area', risk: 'Low', color: 'bg-emerald-500', dot: 'text-emerald-400' },
  ];

  return (
    <div className="relative w-full max-w-[520px] mx-auto animate-float">
      {/* Outer ambient glow */}
      <div className="absolute -inset-6 rounded-3xl bg-emerald-500/6 blur-3xl pointer-events-none" />
      <div className="absolute -inset-3 rounded-3xl bg-emerald-500/4 blur-xl pointer-events-none" />

      {/* Dashboard window */}
      <div className="relative rounded-2xl border border-white/8 bg-charcoal-900/95 shadow-[0_32px_64px_rgba(0,0,0,0.6)] overflow-hidden">
        {/* Window chrome */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5 bg-charcoal-950/70">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/50" />
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500/50" />
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/50" />
          </div>
          <div className="flex-1 mx-4 h-5 bg-white/4 rounded-md flex items-center px-2.5 gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[10px] text-muted-foreground font-mono tracking-tight">
              crimelens.ai/dashboard
            </span>
          </div>
          <div className="text-[10px] text-muted-foreground font-mono opacity-50">
            {new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>

        <div className="p-5 space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <div className="h-2.5 w-28 bg-white/12 rounded-full mb-1.5" />
              <div className="h-1.5 w-16 bg-white/6 rounded-full" />
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-emerald-500/15 rounded-lg border border-emerald-500/25">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] text-emerald-400 font-semibold tracking-wide">LIVE</span>
            </div>
          </div>

          {/* Chart */}
          <div className="h-28 bg-white/2 rounded-xl border border-white/5 p-3 flex items-end gap-1 overflow-hidden">
            {chartValues.map((h, i) => (
              <div
                key={i}
                className="flex-1 rounded-sm transition-all duration-700"
                style={{
                  height: `${h}%`,
                  background: i < activeBars
                    ? i >= activeBars - 2
                      ? 'rgba(16, 185, 129, 0.85)'
                      : 'rgba(16, 185, 129, 0.25)'
                    : 'rgba(255,255,255,0.06)',
                }}
              />
            ))}
          </div>

          {/* Stat pills */}
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: 'Hotspots', val: tick % 2 === 0 ? '24' : '26', accent: 'text-emerald-400' },
              { label: 'Risk Score', val: 'HIGH', accent: 'text-amber-400' },
              { label: 'Alerts', val: tick % 3 === 0 ? '7' : '8', accent: 'text-red-400' },
            ].map((s) => (
              <div key={s.label} className="bg-white/3 rounded-lg p-2.5 border border-white/5 text-center">
                <p className={`text-sm font-bold tabular-nums transition-all duration-300 ${s.accent}`}>{s.val}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5 font-medium">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Activity list */}
          <div className="space-y-1.5">
            {liveItems.map((item) => (
              <div
                key={item.type}
                className="flex items-center gap-3 p-2.5 bg-white/2 rounded-lg border border-white/4 group hover:border-emerald-500/15 transition-colors duration-150"
              >
                <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${item.color}`} />
                <span className="flex-1 text-[11px] text-foreground/75 font-medium">{item.type}</span>
                <span className="text-[10px] text-muted-foreground">{item.loc}</span>
                <span
                  className={`text-[9px] font-semibold tracking-wide px-1.5 py-0.5 rounded-full border ${
                    item.risk === 'High'
                      ? 'text-red-400 border-red-500/20 bg-red-500/10'
                      : item.risk === 'Medium'
                      ? 'text-amber-400 border-amber-500/20 bg-amber-500/10'
                      : 'text-emerald-400 border-emerald-500/20 bg-emerald-500/10'
                  }`}
                >
                  {item.risk}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function HeroSection() {
  const sectionRef = useRef<HTMLDivElement>(null);

  const scrollToCapabilities = () => {
    document.getElementById('capabilities')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section
      id="overview"
      ref={sectionRef}
      className="relative min-h-screen flex items-center pt-16 overflow-hidden"
    >
      {/* Background grid */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px)
          `,
          backgroundSize: '48px 48px',
        }}
      />
      {/* Radial vignette */}
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(ellipse_80%_50%_at_50%_-10%,rgba(16,185,129,0.06),transparent)]" />
      <div className="absolute bottom-0 left-0 right-0 h-32 pointer-events-none bg-gradient-to-t from-background to-transparent" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32 w-full">
        <div className="grid lg:grid-cols-2 gap-16 xl:gap-24 items-center">
          {/* Left: Copy */}
          <div className="animate-slide-up">
            {/* Eyebrow */}
            <div className="mb-8">
              <Badge variant="emerald">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                AI-POWERED CRIME INTELLIGENCE
              </Badge>
            </div>

            {/* Headline */}
            <h1 className="text-5xl md:text-6xl lg:text-[64px] font-bold tracking-[-0.03em] leading-[1.05] text-foreground mb-6">
              See Patterns.{' '}
              <span className="text-emerald-gradient">Understand</span>{' '}
              Crime.
            </h1>

            {/* Description */}
            <p className="text-lg text-muted-foreground leading-relaxed mb-10 max-w-lg">
              Analyze crime data with deep learning to uncover trends, hotspots,
              and predictive insights in one intelligent workspace.
            </p>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row gap-3">
              <Link to="/login">
                <Button
                  variant="primary"
                  size="lg"
                  className="gap-2 w-full sm:w-auto font-semibold"
                  id="hero-explore-btn"
                >
                  Explore CrimeLens
                  <ArrowRight size={16} />
                </Button>
              </Link>
              <button
                onClick={scrollToCapabilities}
                className="inline-flex items-center justify-center gap-2 h-11 px-6 text-sm font-medium text-muted-foreground hover:text-foreground border border-border hover:border-white/15 rounded-lg transition-all duration-200 hover:bg-white/3"
                id="hero-how-it-works-btn"
              >
                See How It Works
                <ChevronDown size={15} />
              </button>
            </div>
          </div>

          {/* Right: Dashboard preview */}
          <div className="animate-fade-in hidden lg:block">
            <DashboardPreview />
          </div>
        </div>
      </div>
    </section>
  );
}

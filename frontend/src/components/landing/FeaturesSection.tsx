import { useState } from 'react';
import { TrendingUp, MapPin, Brain, FolderSearch } from 'lucide-react';

type Capability = {
  id: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  description: string;
  preview: React.ReactNode;
};

// Inline micro-previews for each capability card
function TrendsPreview() {
  const bars = [28, 42, 35, 60, 52, 71, 65, 84, 76, 90, 82, 95];
  return (
    <div className="h-16 flex items-end gap-1 px-1">
      {bars.map((h, i) => (
        <div
          key={i}
          className="flex-1 rounded-sm transition-all duration-500"
          style={{
            height: `${h}%`,
            background:
              i >= bars.length - 3
                ? 'rgba(16,185,129,0.75)'
                : 'rgba(16,185,129,0.18)',
          }}
        />
      ))}
    </div>
  );
}

function HotspotPreview() {
  const dots = [
    { x: 30, y: 40, size: 16, opacity: 0.7 },
    { x: 55, y: 25, size: 22, opacity: 0.85 },
    { x: 70, y: 60, size: 12, opacity: 0.5 },
    { x: 20, y: 65, size: 10, opacity: 0.45 },
    { x: 82, y: 35, size: 8, opacity: 0.35 },
  ];
  return (
    <div className="h-16 relative rounded-lg overflow-hidden border border-white/5 bg-white/2">
      {dots.map((dot, i) => (
        <div
          key={i}
          className="absolute rounded-full"
          style={{
            left: `${dot.x}%`,
            top: `${dot.y}%`,
            width: dot.size,
            height: dot.size,
            transform: 'translate(-50%, -50%)',
            background: `rgba(16,185,129,${dot.opacity})`,
            boxShadow: `0 0 ${dot.size * 2}px rgba(16,185,129,${dot.opacity * 0.5})`,
          }}
        />
      ))}
      <div className="absolute inset-0"
        style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)',
          backgroundSize: '20px 20px',
        }}
      />
    </div>
  );
}

function PredictionPreview() {
  const line = [40, 45, 42, 55, 60, 52, 68, 72, 69, 80, 76, 85];
  const points = line.map((v, i) => `${(i / (line.length - 1)) * 100},${100 - v}`);
  return (
    <div className="h-16 px-1">
      <svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none">
        <defs>
          <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(16,185,129,0.3)" />
            <stop offset="100%" stopColor="rgba(16,185,129,0)" />
          </linearGradient>
        </defs>
        <polyline
          points={points.join(' ')}
          fill="none"
          stroke="rgba(16,185,129,0.7)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
        <polygon
          points={`0,100 ${points.join(' ')} 100,100`}
          fill="url(#lineGrad)"
        />
      </svg>
    </div>
  );
}

function InvestigationPreview() {
  const items = [
    { label: 'Case #1042', status: 'Active', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
    { label: 'Evidence Link', status: 'Pending', color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
    { label: 'Suspect Match', status: 'Found', color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
  ];
  return (
    <div className="space-y-1.5">
      {items.map((item) => (
        <div key={item.label} className="flex items-center justify-between px-2.5 py-1.5 bg-white/2 rounded-lg border border-white/5">
          <span className="text-[11px] text-foreground/60 font-medium">{item.label}</span>
          <span className={`text-[9px] font-semibold tracking-wide px-1.5 py-0.5 rounded-full border ${item.color}`}>
            {item.status}
          </span>
        </div>
      ))}
    </div>
  );
}

const capabilities: Capability[] = [
  {
    id: 'trends',
    icon: TrendingUp,
    title: 'Crime Trends',
    description: 'Identify temporal patterns across historical crime records with multi-dimensional time-series analysis.',
    preview: <TrendsPreview />,
  },
  {
    id: 'hotspot',
    icon: MapPin,
    title: 'Hotspot Analysis',
    description: 'Explore geographic concentrations and emerging crime hotspots through AI-driven spatial intelligence.',
    preview: <HotspotPreview />,
  },
  {
    id: 'prediction',
    icon: Brain,
    title: 'Crime Prediction',
    description: 'Generate probabilistic forecasts from historical patterns using deep learning temporal models.',
    preview: <PredictionPreview />,
  },
  {
    id: 'investigation',
    icon: FolderSearch,
    title: 'Investigation Assistant',
    description: 'Organize and analyze crime information to support structured investigation workflows.',
    preview: <InvestigationPreview />,
  },
];

export function FeaturesSection() {
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <section id="capabilities" className="landing-section section-divider">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="max-w-xl mb-16">
          <p className="text-xs font-semibold text-emerald-500 tracking-[0.15em] uppercase mb-4">
            Capabilities
          </p>
          <h2 className="text-4xl md:text-[44px] font-bold tracking-tight leading-tight text-foreground mb-5">
            One Workspace.{' '}
            <span className="text-muted-foreground font-normal">Multiple Crime Insights.</span>
          </h2>
          <p className="text-base text-muted-foreground leading-relaxed">
            Explore different dimensions of crime data through interactive intelligence tools built for depth and precision.
          </p>
        </div>

        {/* Capability cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger-children">
          {capabilities.map((cap) => (
            <div
              key={cap.id}
              className="capability-card group animate-fade-in"
              onMouseEnter={() => setHovered(cap.id)}
              onMouseLeave={() => setHovered(null)}
            >
              {/* Icon + title */}
              <div className="flex items-start justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/8 border border-emerald-500/15 flex items-center justify-center group-hover:bg-emerald-500/15 group-hover:border-emerald-500/25 transition-all duration-300">
                  <cap.icon size={18} className="text-emerald-500" />
                </div>
              </div>

              <h3 className="text-sm font-semibold text-foreground mb-2">{cap.title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed mb-5">{cap.description}</p>

              {/* Data preview — fades in on hover */}
              <div
                className="transition-all duration-400 overflow-hidden"
                style={{
                  maxHeight: hovered === cap.id ? '80px' : '0px',
                  opacity: hovered === cap.id ? 1 : 0,
                  marginTop: hovered === cap.id ? '0' : '-4px',
                }}
              >
                <div className="pt-3 border-t border-white/5">
                  {cap.preview}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

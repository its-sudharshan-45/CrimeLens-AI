import { X, Check } from 'lucide-react';

const traditional = [
  'Manual case file review',
  'Reactive investigation approach',
  'Siloed data across departments',
  'Time-intensive pattern analysis',
  'Paper-based evidence tracking',
  'Limited cross-case linking',
  'Delayed resource allocation',
];

const aiAssisted = [
  'Automated data synthesis & analysis',
  'Proactive crime prevention insights',
  'Centralized, integrated data platform',
  'Real-time AI pattern recognition',
  'Digital evidence chain-of-custody',
  'Intelligent cross-case correlation',
  'Optimized, data-driven deployment',
];

const highlights = [
  { metric: '10×', label: 'Faster Analysis' },
  { metric: '94.7%', label: 'Prediction Accuracy' },
  { metric: '60%', label: 'Reduced Response Time' },
  { metric: '3×', label: 'More Cases Solved' },
];

export function ComparisonSection() {
  return (
    <section className="py-24 section-divider">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <p className="text-sm font-semibold text-emerald-500 tracking-widest uppercase mb-3">
            Why CrimeLens AI
          </p>
          <h2 className="heading-lg text-foreground mb-4">
            Transform Your Investigation Capability
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto text-base leading-relaxed">
            See how AI-assisted investigation compares to traditional methods across
            key operational dimensions.
          </p>
        </div>

        {/* Comparison Grid */}
        <div className="grid md:grid-cols-2 gap-6 mb-14">
          {/* Traditional */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <div className="w-8 h-8 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center">
                <X size={14} className="text-red-400" />
              </div>
              <h3 className="text-base font-semibold text-foreground">Traditional Investigation</h3>
            </div>
            <ul className="space-y-3">
              {traditional.map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <X size={14} className="text-red-400/60 shrink-0 mt-0.5" />
                  <span className="text-sm text-muted-foreground">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* AI-Assisted */}
          <div className="bg-card border border-emerald-500/20 rounded-2xl p-6 shadow-glow-emerald">
            <div className="flex items-center gap-2 mb-6">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                <Check size={14} className="text-emerald-400" />
              </div>
              <h3 className="text-base font-semibold text-foreground">AI-Assisted Investigation</h3>
            </div>
            <ul className="space-y-3">
              {aiAssisted.map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <Check size={14} className="text-emerald-400 shrink-0 mt-0.5" />
                  <span className="text-sm text-foreground/80">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Highlight metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {highlights.map((h) => (
            <div key={h.label} className="text-center p-5 bg-secondary/40 border border-border rounded-xl">
              <p className="text-3xl font-bold text-emerald-gradient mb-1">{h.metric}</p>
              <p className="text-xs text-muted-foreground">{h.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

import { Database, Cpu, BarChart3 } from 'lucide-react';

const steps = [
  {
    number: '01',
    icon: Database,
    title: 'Analyze Data',
    description:
      'Process historical crime records and extract relevant spatial, temporal, and contextual features.',
  },
  {
    number: '02',
    icon: Cpu,
    title: 'Learn Patterns',
    description:
      'Deep-learning models identify temporal, spatial, and feature relationships within the data.',
  },
  {
    number: '03',
    icon: BarChart3,
    title: 'Generate Insights',
    description:
      'Visualize patterns, predictions, hotspots, and investigation intelligence in one workspace.',
  },
];

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="landing-section section-divider">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="max-w-xl mb-16">
          <p className="text-xs font-semibold text-emerald-500 tracking-[0.15em] uppercase mb-4">
            How It Works
          </p>
          <h2 className="text-4xl md:text-[44px] font-bold tracking-tight leading-tight text-foreground mb-5">
            From Crime Data{' '}
            <span className="text-muted-foreground font-normal">to Intelligence.</span>
          </h2>
          <p className="text-base text-muted-foreground leading-relaxed">
            A three-stage intelligence pipeline that transforms raw data into actionable insight.
          </p>
        </div>

        {/* Steps */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative">
          {/* Connector line — desktop only */}
          <div className="hidden md:block absolute top-8 left-[calc(16.66%+20px)] right-[calc(16.66%+20px)] h-px">
            <div
              className="w-full h-full"
              style={{
                background: 'linear-gradient(90deg, rgba(16,185,129,0.3) 0%, rgba(16,185,129,0.5) 50%, rgba(16,185,129,0.3) 100%)',
              }}
            />
            {/* Arrow dots */}
            <div className="absolute top-1/2 left-1/3 -translate-x-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-emerald-500/60" />
            <div className="absolute top-1/2 left-2/3 -translate-x-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-emerald-500/60" />
          </div>

          {steps.map((step, index) => (
            <div
              key={step.number}
              className="relative group animate-fade-in"
              style={{ animationDelay: `${index * 120}ms` }}
            >
              {/* Step container */}
              <div className="bg-card border border-border rounded-2xl p-8 h-full transition-all duration-300 hover:border-emerald-500/25 hover:bg-secondary/30 hover:-translate-y-0.5">
                {/* Number badge + icon */}
                <div className="flex items-center gap-3 mb-6">
                  <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-emerald-500/8 border border-emerald-500/15 group-hover:bg-emerald-500/15 group-hover:border-emerald-500/25 transition-all duration-300">
                    <step.icon size={18} className="text-emerald-500" />
                  </div>
                  <span className="text-xs font-bold text-emerald-500/70 tracking-[0.15em] font-mono">
                    — {step.number}
                  </span>
                </div>

                <h3 className="text-lg font-semibold text-foreground mb-3 tracking-tight">
                  {step.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

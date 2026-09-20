import {
  Database,
  Cpu,
  Network,
  TrendingUp,
  Briefcase,
  CheckCircle2,
} from 'lucide-react';

const steps = [
  {
    icon: Database,
    title: 'Crime Data Collection',
    description: 'Historical crime records, incident reports, geographic data, and contextual factors are ingested from multiple sources.',
  },
  {
    icon: Cpu,
    title: 'AI Analysis',
    description: 'Machine learning models process and normalize data, identifying statistical anomalies and significant variables.',
  },
  {
    icon: Network,
    title: 'Pattern Recognition',
    description: 'Deep learning algorithms detect recurring crime patterns, correlations, and seasonal trends across time and geography.',
  },
  {
    icon: TrendingUp,
    title: 'Crime Prediction',
    description: 'Predictive models generate geo-temporal risk scores, forecasting likely crime type, location, and time window.',
  },
  {
    icon: Briefcase,
    title: 'Investigation Support',
    description: 'AI-generated intelligence links cases, suggests leads, and surfaces relevant evidence to support active investigations.',
  },
  {
    icon: CheckCircle2,
    title: 'Decision Making',
    description: 'Officers and commanders receive actionable, data-driven insights to inform resource allocation and prevention strategies.',
  },
];

export function HowItWorksSection() {
  return (
    <section id="about" className="py-24 bg-secondary/20 section-divider">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <p className="text-sm font-semibold text-emerald-500 tracking-widest uppercase mb-3">
            The Process
          </p>
          <h2 className="heading-lg text-foreground mb-4">How CrimeLens AI Works</h2>
          <p className="text-muted-foreground max-w-xl mx-auto text-base leading-relaxed">
            A six-stage intelligence pipeline transforming raw crime data into
            actionable law enforcement insights.
          </p>
        </div>

        {/* Steps */}
        <div className="relative">
          {/* Vertical connector line */}
          <div className="absolute left-[19px] top-4 bottom-4 w-px bg-border hidden sm:block" />

          <div className="space-y-6">
            {steps.map((step, index) => (
              <div key={step.title} className="relative flex gap-6 group">
                {/* Step number + icon */}
                <div className="relative shrink-0 flex flex-col items-center">
                  <div className="w-10 h-10 rounded-xl bg-card border border-border flex items-center justify-center group-hover:border-emerald-500/30 group-hover:bg-emerald-500/5 transition-all duration-200 relative z-10">
                    <step.icon size={16} className="text-emerald-500" />
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 pb-6 last:pb-0">
                  <div className="flex items-center gap-3 mb-1.5">
                    <span className="text-xs font-semibold text-emerald-500 tracking-wider">
                      STEP {String(index + 1).padStart(2, '0')}
                    </span>
                  </div>
                  <h3 className="text-base font-semibold text-foreground mb-1.5">{step.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

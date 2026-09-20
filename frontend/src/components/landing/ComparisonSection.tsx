// Repurposed as DeepLearningSection — showcases the 4 AI models powering CrimeLens

type Model = {
  id: string;
  acronym: string;
  name: string;
  role: string;
  description: string;
  accent: string;
  bg: string;
  border: string;
};

const models: Model[] = [
  {
    id: 'gru',
    acronym: 'GRU',
    name: 'Gated Recurrent Unit',
    role: 'Temporal Pattern Prediction',
    description:
      'Learns sequential dependencies in crime time-series to forecast likely future crime occurrences across time windows.',
    accent: 'text-emerald-400',
    bg: 'bg-emerald-500/6',
    border: 'border-emerald-500/15',
  },
  {
    id: 'cnn',
    acronym: 'CNN',
    name: 'Convolutional Neural Net',
    role: 'Spatial Hotspot Analysis',
    description:
      'Extracts spatial feature hierarchies from geographic crime data to identify concentrated high-risk zones.',
    accent: 'text-blue-400',
    bg: 'bg-blue-500/6',
    border: 'border-blue-500/15',
  },
  {
    id: 'ft',
    acronym: 'FT-T',
    name: 'FT-Transformer',
    role: 'Complex Feature Relationships',
    description:
      'Applies attention mechanisms to tabular crime features, capturing non-linear relationships across categorical and numerical inputs.',
    accent: 'text-violet-400',
    bg: 'bg-violet-500/6',
    border: 'border-violet-500/15',
  },
  {
    id: 'nbeats',
    acronym: 'N-BEATS',
    name: 'Neural Basis Expansion',
    role: 'Time-Series Forecasting',
    description:
      'Provides interpretable decomposition of crime time-series into trend and seasonality components for precise long-horizon forecasts.',
    accent: 'text-amber-400',
    bg: 'bg-amber-500/6',
    border: 'border-amber-500/15',
  },
];

export function ComparisonSection() {
  return (
    <section id="deep-learning" className="landing-section section-divider bg-secondary/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="max-w-xl mb-16">
          <p className="text-xs font-semibold text-emerald-500 tracking-[0.15em] uppercase mb-4">
            Deep Learning
          </p>
          <h2 className="text-4xl md:text-[44px] font-bold tracking-tight leading-tight text-foreground mb-5">
            Built on{' '}
            <span className="text-muted-foreground font-normal">Deep Learning.</span>
          </h2>
          <p className="text-base text-muted-foreground leading-relaxed">
            Multiple specialized models analyze different dimensions of crime patterns — each optimized for its domain.
          </p>
        </div>

        {/* Model grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {models.map((model, index) => (
            <div
              key={model.id}
              className="model-card group animate-fade-in relative overflow-hidden"
              style={{ animationDelay: `${index * 90}ms` }}
            >
              {/* Subtle corner accent */}
              <div
                className={`absolute top-0 right-0 w-24 h-24 rounded-bl-full opacity-30 pointer-events-none transition-opacity duration-300 group-hover:opacity-50 ${model.bg}`}
              />

              <div className="relative">
                {/* Acronym badge */}
                <div className="flex items-center gap-3 mb-5">
                  <div
                    className={`px-3 py-1.5 rounded-lg text-sm font-bold font-mono tracking-wide border ${model.bg} ${model.border} ${model.accent}`}
                  >
                    {model.acronym}
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold text-muted-foreground tracking-wide uppercase">
                      {model.role}
                    </p>
                  </div>
                </div>

                <h3 className="text-base font-semibold text-foreground mb-2 tracking-tight">
                  {model.name}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {model.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

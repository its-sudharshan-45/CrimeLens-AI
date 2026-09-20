// Repurposed as ResponsibleAISection — "Decision Support, Not Decision Making."

export function SecuritySection() {
  return (
    <section id="responsible-ai" className="landing-section section-divider">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          {/* Eyebrow */}
          <p className="text-xs font-semibold text-emerald-500 tracking-[0.15em] uppercase mb-10">
            Responsible AI
          </p>

          {/* Large quote */}
          <blockquote className="relative">
            {/* Quote mark */}
            <div
              className="absolute -top-4 -left-2 text-[96px] leading-none text-emerald-500/10 font-serif select-none pointer-events-none"
              aria-hidden="true"
            >
              &ldquo;
            </div>

            <h2 className="text-4xl md:text-5xl lg:text-[52px] font-bold tracking-[-0.025em] leading-[1.1] text-foreground mb-8 relative">
              Decision Support,{' '}
              <span className="text-muted-foreground font-normal">Not Decision Making.</span>
            </h2>
          </blockquote>

          {/* Disclaimer */}
          <div className="border-l-2 border-emerald-500/30 pl-6">
            <p className="text-base text-muted-foreground leading-relaxed max-w-2xl">
              CrimeLens AI provides probabilistic insights based on available data. Predictions are
              intended to support human analysis and should be interpreted alongside verified evidence,
              investigation context, and professional judgment.
            </p>
          </div>

          {/* Subtle visual separator */}
          <div className="mt-12 flex items-center gap-4">
            <div className="flex-1 h-px bg-border" />
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-secondary/40 border border-border">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/60" />
              <span className="text-xs text-muted-foreground font-medium">Human-centered intelligence</span>
            </div>
            <div className="flex-1 h-px bg-border" />
          </div>
        </div>
      </div>
    </section>
  );
}

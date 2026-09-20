// Repurposed as FinalCTASection + minimal footer bar
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { Logo } from '@/components/common/Logo';
import { Button } from '@/components/ui/Button';

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <>
      {/* Final CTA section */}
      <section id="cta" className="landing-section section-divider relative overflow-hidden">
        {/* Background treatment */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_60%_at_50%_100%,rgba(16,185,129,0.07),transparent)]" />
          <div
            className="absolute inset-0 opacity-50"
            style={{
              backgroundImage: `
                linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px)
              `,
              backgroundSize: '40px 40px',
            }}
          />
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          {/* Eyebrow */}
          <p className="text-xs font-semibold text-emerald-500 tracking-[0.15em] uppercase mb-8">
            Get Started
          </p>

          {/* Headline */}
          <h2 className="text-4xl md:text-5xl lg:text-[56px] font-bold tracking-[-0.03em] leading-[1.05] text-foreground mb-6 max-w-2xl mx-auto">
            Explore{' '}
            <span className="text-emerald-gradient">CrimeLens</span>{' '}
            AI
          </h2>

          <p className="text-lg text-muted-foreground leading-relaxed mb-10 max-w-lg mx-auto">
            Turn complex crime data into insights you can explore.
          </p>

          {/* CTA */}
          <Link to="/dashboard">
            <Button
              variant="primary"
              size="lg"
              className="gap-2 font-semibold text-base px-8 h-12"
              id="final-cta-btn"
            >
              Open CrimeLens Dashboard
              <ArrowRight size={16} />
            </Button>
          </Link>
        </div>
      </section>

      {/* Minimal footer bar */}
      <footer className="border-t border-border bg-charcoal-950/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <Logo size="sm" />
            <p className="text-xs text-muted-foreground">
              &copy; {currentYear} CrimeLens AI. Decision support for human analysts.
            </p>
          </div>
        </div>
      </footer>
    </>
  );
}

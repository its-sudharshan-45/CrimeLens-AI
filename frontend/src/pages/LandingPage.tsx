import { Link } from 'react-router-dom';
import { ArrowRight, BarChart3, Brain, MapPin, ShieldCheck } from 'lucide-react';

import { Logo } from '@/components/common/Logo';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/hooks/useAuth';

const datasetStats = [
  { label: 'Historical incidents', value: '40,160' },
  { label: 'Districts covered', value: '29' },
  { label: 'States covered', value: '15' },
  { label: 'Forecast horizon', value: '7 days' },
];

const capabilities = [
  {
    icon: MapPin,
    title: 'State and district selection',
    description:
      'Choose from the 29 city-level scopes the trained model was evaluated on, mapped to their Indian state and district.',
  },
  {
    icon: Brain,
    title: 'Trained GRU forecaster',
    description:
      'A PyTorch GRU predicts the next seven days of incidents from each district\u2019s historical series.',
  },
  {
    icon: BarChart3,
    title: 'Transparent risk index',
    description:
      'The risk percentage is a relative index computed from the predicted daily incident volume across all districts.',
  },
];

export default function LandingPage() {
  const { user } = useAuth();
  const primaryHref = user ? '/dashboard' : '/login';
  const primaryLabel = user ? 'Open dashboard' : 'Sign in to predict';

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between px-4 sm:px-6">
          <Logo size="md" />
          <nav className="flex items-center gap-2">
            {!user && (
              <Link
                to="/signup"
                className="hidden rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground sm:inline-flex"
              >
                Create account
              </Link>
            )}
            <Link to={primaryHref}>
              <Button size="sm">{primaryLabel}</Button>
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl px-4 sm:px-6">
        <section className="py-16 sm:py-20">
          <Badge variant="emerald" dot>
            Deep learning &middot; Crime risk prediction
          </Badge>

          <h1 className="mt-5 max-w-3xl text-3xl font-bold leading-tight tracking-tight sm:text-5xl">
            District-level crime risk,
            <span className="text-emerald-500"> grounded in real data.</span>
          </h1>

          <p className="mt-5 max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
            CrimeLens AI uses a trained PyTorch GRU model and a public Indian crime dataset to estimate
            near-term incident volume. Select a state and district to see a relative risk index, a
            Low/Medium/High category, and the underlying seven-day forecast.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link to={primaryHref}>
              <Button size="lg" className="w-full sm:w-auto">
                {primaryLabel}
                <ArrowRight size={15} />
              </Button>
            </Link>
            <a href="#how-it-works">
              <Button variant="outline" size="lg" className="w-full sm:w-auto">
                How it works
              </Button>
            </a>
          </div>
        </section>

        <section aria-label="Dataset summary" className="grid grid-cols-2 gap-3 pb-16 sm:grid-cols-4">
          {datasetStats.map((stat) => (
            <div key={stat.label} className="rounded-xl border border-border bg-card p-4">
              <p className="text-xl font-bold text-foreground sm:text-2xl">{stat.value}</p>
              <p className="mt-0.5 text-[11px] text-muted-foreground">{stat.label}</p>
            </div>
          ))}
        </section>

        <section id="how-it-works" className="border-t border-border py-14">
          <h2 className="text-xl font-semibold tracking-tight">What the dashboard does</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            One focused workflow: choose a location, run the model, and read the result.
          </p>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {capabilities.map(({ icon: Icon, title, description }) => (
              <div key={title} className="rounded-xl border border-border bg-card p-5">
                <div className="inline-flex rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-2 text-emerald-400">
                  <Icon size={17} />
                </div>
                <h3 className="mt-3 text-sm font-semibold text-foreground">{title}</h3>
                <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{description}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="border-t border-border py-14">
          <div className="flex flex-col gap-4 rounded-xl border border-border bg-card p-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <div className="rounded-lg border border-border bg-secondary p-2 text-muted-foreground">
                <ShieldCheck size={18} />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-foreground">Decision support, not decision making</h2>
                <p className="mt-1 max-w-xl text-xs leading-relaxed text-muted-foreground">
                  The risk index is not a probability of crime and must not be used for individual profiling.
                  It summarizes predicted incident volume for a district.
                </p>
              </div>
            </div>
            <Link to={primaryHref} className="shrink-0">
              <Button variant="secondary" size="sm">
                {primaryLabel}
              </Button>
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-1 px-4 py-5 text-[11px] text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <span>CrimeLens AI &middot; Deep learning&ndash;based district crime risk prediction</span>
          <span>College project &middot; For review and demonstration</span>
        </div>
      </footer>
    </div>
  );
}

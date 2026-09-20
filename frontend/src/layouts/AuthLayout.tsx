import { Outlet, Link } from 'react-router-dom';
import { Logo } from '@/components/common/Logo';
import { ShieldCheck, Brain, Activity } from 'lucide-react';

const brandPoints = [
  {
    icon: Brain,
    title: 'AI-Powered Predictions',
    description: 'Machine learning models with 94.7% accuracy in crime forecasting.',
  },
  {
    icon: ShieldCheck,
    title: 'Enterprise Security',
    description: 'End-to-end encrypted, secure authenticated access, and full audit logging.',
  },
  {
    icon: Activity,
    title: 'Real-Time Intelligence',
    description: 'Live crime feed, hotspot detection, and investigation dashboards.',
  },
];

export default function AuthLayout() {
  return (
    <div className="min-h-screen bg-background flex">
      {/* Left Panel — Brand */}
      <div className="hidden lg:flex lg:w-[45%] xl:w-[42%] flex-col justify-between p-10 bg-charcoal-900 border-r border-border bg-dots relative overflow-hidden">
        {/* Ambient glow */}
        <div className="absolute top-0 left-0 w-72 h-72 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-48 h-48 bg-emerald-500/4 rounded-full blur-2xl pointer-events-none" />

        {/* Top: Logo */}
        <div className="relative">
          <Link to="/">
            <Logo size="lg" />
          </Link>
        </div>

        {/* Middle: Brand messaging */}
        <div className="relative space-y-8">
          <div>
            <h2 className="text-2xl font-bold text-foreground leading-snug mb-3">
              Intelligence-Grade<br />Law Enforcement Platform
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-sm">
              Trusted by agencies nationwide for crime prediction, evidence management,
              and AI-assisted investigations.
            </p>
          </div>

          <div className="space-y-5">
            {brandPoints.map((point) => (
              <div key={point.title} className="flex items-start gap-4">
                <div className="w-9 h-9 rounded-lg bg-emerald-500/8 border border-emerald-500/12 flex items-center justify-center shrink-0">
                  <point.icon size={15} className="text-emerald-500" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground/90 mb-0.5">{point.title}</p>
                  <p className="text-xs text-muted-foreground leading-relaxed">{point.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom: Footer note */}
        <div className="relative">
          <p className="text-xs text-muted-foreground">
            &copy; {new Date().getFullYear()} CrimeLens AI. All rights reserved.
          </p>
        </div>
      </div>

      {/* Right Panel — Auth Form */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 sm:p-10 bg-background overflow-y-auto">
        {/* Mobile-only logo */}
        <div className="lg:hidden mb-8">
          <Link to="/">
            <Logo size="lg" />
          </Link>
        </div>

        {/* Form content injected here */}
        <div className="w-full max-w-md">
          <Outlet />
        </div>
      </div>
    </div>
  );
}

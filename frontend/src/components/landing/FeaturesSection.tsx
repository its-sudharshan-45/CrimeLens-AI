import {
  TrendingUp,
  BarChart3,
  MapPin,
  FolderSearch,
  ClipboardList,
  ShieldCheck,
  Brain,
  Lock,
} from 'lucide-react';

const features = [
  {
    icon: TrendingUp,
    title: 'Crime Prediction',
    description:
      'Advanced ML models predict crime likelihood in specific areas and time windows, enabling proactive policing strategies.',
  },
  {
    icon: BarChart3,
    title: 'Crime Analytics',
    description:
      'Comprehensive dashboards providing deep statistical analysis of crime patterns, trends, and emerging threat indicators.',
  },
  {
    icon: MapPin,
    title: 'Hotspot Detection',
    description:
      'Real-time geospatial analysis identifies high-risk zones with AI-generated risk scores and patrol recommendations.',
  },
  {
    icon: FolderSearch,
    title: 'Evidence Management',
    description:
      'Secure, structured digital evidence chain-of-custody with version control, access logs, and cloud storage.',
  },
  {
    icon: ClipboardList,
    title: 'Investigation Management',
    description:
      'Streamlined case tracking from initial report to resolution, linking evidence, suspects, and case notes in one platform.',
  },
  {
    icon: ShieldCheck,
    title: 'Audit & Activity Tracking',
    description:
      'Comprehensive audit trails ensure all system events, evidence interactions, and case updates are logged with tamper-proof records.',
  },
  {
    icon: Brain,
    title: 'AI Intelligence Dashboard',
    description:
      'Unified intelligence view synthesizing crime predictions, active investigations, and AI recommendations.',
  },
  {
    icon: Lock,
    title: 'Secure Authentication',
    description:
      'Multi-factor authentication, JWT sessions, Google OAuth, and automated session management protect agency data.',
  },
];

export function FeaturesSection() {
  return (
    <section id="features" className="py-24 section-divider">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <p className="text-sm font-semibold text-emerald-500 tracking-widest uppercase mb-3">
            Platform Capabilities
          </p>
          <h2 className="heading-lg text-foreground mb-4">
            Everything Your Agency Needs
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto text-base leading-relaxed">
            An integrated suite of AI-powered tools designed for modern law enforcement —
            from predictive analytics to secure evidence management.
          </p>
        </div>

        {/* Feature grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((feature) => (
            <div key={feature.title} className="feature-card group">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/15 flex items-center justify-center mb-4 group-hover:bg-emerald-500/15 transition-colors duration-200">
                <feature.icon size={18} className="text-emerald-500" />
              </div>
              <h3 className="text-sm font-semibold text-foreground mb-2">{feature.title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

import {
  KeyRound,
  ShieldCheck,
  HardDriveDownload,
  ScrollText,
  FileKey,
  Globe,
  BadgeCheck,
} from 'lucide-react';

const securityFeatures = [
  {
    icon: KeyRound,
    title: 'Encrypted Authentication',
    description: 'Industry-standard bcrypt password hashing and TLS-encrypted data transmission protect all credentials.',
  },
  {
    icon: ShieldCheck,
    title: 'Secure Access Control',
    description: 'Verified authentication ensures only authorized personnel access sensitive investigation data and system capabilities.',
  },
  {
    icon: HardDriveDownload,
    title: 'Secure Evidence Storage',
    description: 'Evidence files stored in encrypted cloud storage with signed URLs and strict access policies.',
  },
  {
    icon: ScrollText,
    title: 'Audit Logging',
    description: 'Every system action is logged with user identity, timestamp, and IP address for full accountability.',
  },
  {
    icon: FileKey,
    title: 'JWT Verification',
    description: 'Stateless JWT tokens with automatic refresh and server-side validation prevent unauthorized access.',
  },
  {
    icon: Globe,
    title: 'Protected APIs',
    description: 'All backend endpoints enforce authentication middleware, rate limiting, and CORS policies.',
  },
];

export function SecuritySection() {
  return (
    <section id="security" className="py-24 bg-secondary/20 section-divider">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <p className="text-sm font-semibold text-emerald-500 tracking-widest uppercase mb-3">
            Enterprise Security
          </p>
          <h2 className="heading-lg text-foreground mb-4">
            Built for High-Stakes Environments
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto text-base leading-relaxed">
            CrimeLens AI implements defense-in-depth security principles across every layer —
            from authentication to storage to API access.
          </p>
        </div>

        {/* Security tiles */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-12">
          {securityFeatures.map((feature) => (
            <div
              key={feature.title}
              className="bg-card border border-border rounded-xl p-5 hover:border-emerald-500/20 transition-all duration-200 group"
            >
              <div className="flex items-start gap-4">
                <div className="w-9 h-9 rounded-lg bg-emerald-500/8 border border-emerald-500/12 flex items-center justify-center shrink-0 group-hover:bg-emerald-500/12 transition-colors">
                  <feature.icon size={16} className="text-emerald-500" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-1.5">{feature.title}</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">{feature.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Certification badge row */}
        <div className="flex flex-wrap items-center justify-center gap-4">
          {['Enterprise Grade', 'SOC 2 Ready', 'GDPR Compliant', 'End-to-End Encrypted'].map((cert) => (
            <div
              key={cert}
              className="flex items-center gap-2 px-4 py-2 rounded-full bg-card border border-border text-sm text-muted-foreground"
            >
              <BadgeCheck size={14} className="text-emerald-500" />
              {cert}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

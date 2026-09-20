import { Link } from 'react-router-dom';
import { Mail, ExternalLink } from 'lucide-react';
import { Logo } from '@/components/common/Logo';

const quickLinks = [
  { label: 'Features', href: '#features' },
  { label: 'Security', href: '#security' },
  { label: 'How It Works', href: '#about' },
];

const legalLinks = [
  { label: 'Privacy Policy', href: '#' },
  { label: 'Terms of Service', href: '#' },
];

function GithubIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-charcoal-950/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
          {/* Brand column */}
          <div className="md:col-span-2">
            <Logo size="md" className="mb-4" />
            <p className="text-sm text-muted-foreground leading-relaxed max-w-xs">
              AI-powered crime prediction and investigation platform for modern law enforcement agencies.
              Trusted by departments across the nation.
            </p>
            <div className="flex items-center gap-3 mt-5">
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="w-8 h-8 rounded-lg bg-secondary border border-border flex items-center justify-center text-muted-foreground hover:text-foreground hover:border-emerald-500/30 transition-all duration-150"
                aria-label="GitHub"
              >
                <GithubIcon size={14} />
              </a>
              <a
                href="mailto:contact@crimelens.ai"
                className="w-8 h-8 rounded-lg bg-secondary border border-border flex items-center justify-center text-muted-foreground hover:text-foreground hover:border-emerald-500/30 transition-all duration-150"
                aria-label="Contact"
              >
                <Mail size={14} />
              </a>
            </div>
          </div>

          {/* Platform links */}
          <div>
            <h4 className="text-xs font-semibold text-foreground/70 tracking-widest uppercase mb-4">Platform</h4>
            <ul className="space-y-2.5">
              {quickLinks.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-150"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
              <li>
                <Link to="/login" className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-150">
                  Sign In
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="text-xs font-semibold text-foreground/70 tracking-widest uppercase mb-4">Legal</h4>
            <ul className="space-y-2.5">
              {legalLinks.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-150 inline-flex items-center gap-1"
                  >
                    {link.label}
                    <ExternalLink size={10} />
                  </a>
                </li>
              ))}
              <li>
                <a
                  href="mailto:contact@crimelens.ai"
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-150"
                >
                  Contact Us
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between pt-6 border-t border-border gap-3">
          <p className="text-xs text-muted-foreground">
            &copy; {currentYear} CrimeLens AI. All rights reserved.
          </p>
          <p className="text-xs text-muted-foreground">
            Built for law enforcement. Secured by Supabase.
          </p>
        </div>
      </div>
    </footer>
  );
}

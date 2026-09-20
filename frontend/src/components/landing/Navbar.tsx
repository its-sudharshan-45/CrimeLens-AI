import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, ExternalLink } from 'lucide-react';
import { Logo } from '@/components/common/Logo';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

const navLinks = [
  { label: 'Overview', href: '#overview' },
  { label: 'Capabilities', href: '#capabilities' },
  { label: 'How It Works', href: '#how-it-works' },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [location]);

  const handleAnchor = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (href.startsWith('#')) {
      e.preventDefault();
      document.querySelector(href)?.scrollIntoView({ behavior: 'smooth' });
      setMobileOpen(false);
    }
  };

  return (
    <header
      className={cn(
        'fixed top-0 left-0 right-0 z-50 transition-all duration-500',
        scrolled
          ? 'bg-charcoal-950/85 backdrop-blur-xl border-b border-white/5 shadow-[0_1px_0_rgba(255,255,255,0.04)]'
          : 'bg-transparent'
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Logo size="md" />

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                onClick={(e) => handleAnchor(e, link.href)}
                className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors duration-150 rounded-lg hover:bg-white/4"
              >
                {link.label}
              </a>
            ))}
          </nav>

          {/* Desktop CTA */}
          <div className="hidden md:flex items-center gap-3">
            <Link to="/login">
              <Button variant="ghost" size="sm" id="nav-login-btn" className="text-muted-foreground hover:text-foreground">
                Log In
              </Button>
            </Link>
            <Link to="/dashboard">
              <Button
                variant="primary"
                size="sm"
                id="nav-open-dashboard-btn"
                className="gap-1.5 font-medium"
              >
                Open Dashboard
                <ExternalLink size={12} />
              </Button>
            </Link>
          </div>

          {/* Mobile Toggle */}
          <button
            className="md:hidden p-2 text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-white/4"
            onClick={() => setMobileOpen((o) => !o)}
            aria-label="Toggle menu"
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="md:hidden bg-charcoal-950/95 backdrop-blur-xl border-t border-white/5 animate-slide-up">
          <div className="px-4 py-4 space-y-1">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                onClick={(e) => handleAnchor(e, link.href)}
                className="block px-3 py-2.5 text-sm text-muted-foreground hover:text-foreground hover:bg-white/4 rounded-lg transition-colors"
              >
                {link.label}
              </a>
            ))}
            <div className="pt-3 border-t border-border flex flex-col gap-2 mt-2">
              <Link to="/login">
                <Button variant="outline" size="md" className="w-full">Log In</Button>
              </Link>
              <Link to="/dashboard">
                <Button variant="primary" size="md" className="w-full gap-1.5">
                  Open Dashboard
                  <ExternalLink size={12} />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

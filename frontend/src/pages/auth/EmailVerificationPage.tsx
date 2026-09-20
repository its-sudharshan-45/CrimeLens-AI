import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { toast } from 'sonner';
import { Mail, CheckCircle2, RefreshCw } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/Button';

const RESEND_COOLDOWN = 60; // seconds

export default function EmailVerificationPage() {
  const { user, resendVerification, isEmailVerified } = useAuth();
  const location = useLocation();
  const emailFromState = (location.state as { email?: string })?.email;
  const displayEmail = user?.email ?? emailFromState ?? '';

  const [isResending, setIsResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  // Start cooldown timer
  useEffect(() => {
    if (cooldown > 0) {
      const timer = setTimeout(() => setCooldown((c) => c - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [cooldown]);

  const handleResend = async () => {
    if (cooldown > 0) return;
    setIsResending(true);
    try {
      await resendVerification();
      toast.success('Verification email sent! Check your inbox.');
      setCooldown(RESEND_COOLDOWN);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to resend. Try again shortly.';
      toast.error(msg);
    } finally {
      setIsResending(false);
    }
  };

  // If email is already verified, show success
  if (isEmailVerified) {
    return (
      <div className="animate-slide-up text-center">
        <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-5">
          <CheckCircle2 size={28} className="text-emerald-500" />
        </div>
        <h1 className="text-2xl font-bold text-foreground mb-3">Email Verified</h1>
        <p className="text-sm text-muted-foreground mb-8 leading-relaxed max-w-xs mx-auto">
          Your email address has been verified. You can now access your CrimeLens AI dashboard.
        </p>
        <Link to="/dashboard">
          <Button variant="primary" size="lg" id="go-to-dashboard-btn">
            Go to Dashboard
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-slide-up text-center">
      {/* Icon */}
      <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-5">
        <Mail size={28} className="text-emerald-500" />
      </div>

      {/* Content */}
      <h1 className="text-2xl font-bold text-foreground mb-3">Verify Your Email</h1>
      <p className="text-sm text-muted-foreground mb-2 leading-relaxed">
        We sent a verification link to:
      </p>
      {displayEmail && (
        <p className="text-sm font-semibold text-foreground mb-5">{displayEmail}</p>
      )}
      <p className="text-xs text-muted-foreground mb-8 leading-relaxed max-w-xs mx-auto">
        Click the link in your email to verify your account. 
        You must verify your email before accessing the platform.
        Check your spam folder if you don't see it.
      </p>

      {/* Resend button */}
      <div className="space-y-3">
        <Button
          variant="primary"
          size="lg"
          loading={isResending}
          disabled={cooldown > 0}
          onClick={handleResend}
          className="w-full max-w-xs mx-auto"
          id="resend-verification-btn"
        >
          {!isResending && <RefreshCw size={15} />}
          {cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend Verification Email'}
        </Button>

        <div className="text-center">
          <Link
            to="/login"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Back to Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}

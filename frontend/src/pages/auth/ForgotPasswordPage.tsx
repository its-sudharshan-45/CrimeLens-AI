import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { CheckCircle2, ArrowLeft, Mail } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';

const forgotPasswordSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
});

type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPasswordPage() {
  const { resetPassword } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [sentEmail, setSentEmail] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data: ForgotPasswordFormData) => {
    setIsLoading(true);
    try {
      await resetPassword(data);
      setSentEmail(data.email);
      setEmailSent(true);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to send reset email.';
      toast.error(msg);
    } finally {
      setIsLoading(false);
    }
  };

  if (emailSent) {
    return (
      <div className="animate-slide-up text-center">
        <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-5">
          <CheckCircle2 size={24} className="text-emerald-500" />
        </div>
        <h1 className="text-2xl font-bold text-foreground mb-3">Check Your Email</h1>
        <p className="text-sm text-muted-foreground mb-2 leading-relaxed">
          We've sent a password reset link to:
        </p>
        <p className="text-sm font-medium text-foreground mb-6">{sentEmail}</p>
        <p className="text-xs text-muted-foreground mb-8 leading-relaxed max-w-xs mx-auto">
          Click the link in the email to reset your password.
          The link expires in 60 minutes. Check your spam folder if you don't see it.
        </p>
        <Button
          variant="outline"
          size="md"
          onClick={() => setEmailSent(false)}
          className="mb-4"
          id="resend-reset-btn"
        >
          Send another email
        </Button>
        <div>
          <Link to="/login" className="text-sm text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1.5">
            <ArrowLeft size={14} />
            Back to Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-slide-up">
      {/* Header */}
      <div className="mb-8">
        <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-5">
          <Mail size={20} className="text-emerald-500" />
        </div>
        <h1 className="text-2xl font-bold text-foreground mb-2">Reset Password</h1>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Enter your registered email address and we'll send you a secure link to reset your password.
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <div>
          <Label htmlFor="forgot-email" required>Email Address</Label>
          <Input
            id="forgot-email"
            type="email"
            placeholder="officer@agency.gov"
            autoComplete="email"
            error={errors.email?.message}
            {...register('email')}
          />
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          loading={isLoading}
          className="w-full"
          id="forgot-password-submit-btn"
        >
          Send Reset Link
        </Button>
      </form>

      {/* Back to login */}
      <div className="mt-6 text-center">
        <Link
          to="/login"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1.5"
        >
          <ArrowLeft size={14} />
          Back to Sign In
        </Link>
      </div>
    </div>
  );
}

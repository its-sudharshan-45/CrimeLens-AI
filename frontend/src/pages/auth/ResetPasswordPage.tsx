import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { CheckCircle2, KeyRound, AlertTriangle } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/lib/supabase';
import { Button } from '@/components/ui/Button';
import { Label } from '@/components/ui/Label';
import { PasswordInput } from '@/components/common/PasswordInput';
import { PasswordStrengthIndicator } from '@/components/common/PasswordStrengthIndicator';

const resetSchema = z
  .object({
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
      .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
      .regex(/\d/, 'Password must contain at least one number')
      .regex(/[^A-Za-z0-9]/, 'Password must contain at least one special character'),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

type ResetFormData = z.infer<typeof resetSchema>;

export default function ResetPasswordPage() {
  const { updatePassword } = useAuth();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [hasSession, setHasSession] = useState<boolean | null>(null);

  // Supabase sends tokens in URL hash on recovery flow
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY') {
        setHasSession(true);
      }
    });

    // Check if we already have a session (user arrived here with valid token)
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) {
        setHasSession(true);
      } else {
        // Give the auth state change a moment to fire first
        setTimeout(() => {
          setHasSession((prev) => prev ?? false);
        }, 500);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ResetFormData>({
    resolver: zodResolver(resetSchema),
    mode: 'onChange',
  });

  const watchedPassword = watch('password', '');

  const onSubmit = async (data: ResetFormData) => {
    setIsLoading(true);
    try {
      await updatePassword(data);
      setSuccess(true);
      toast.success('Password updated successfully!');
      setTimeout(() => navigate('/login'), 2500);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to update password.';
      toast.error(msg);
    } finally {
      setIsLoading(false);
    }
  };

  // Loading state while checking session
  if (hasSession === null) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // Invalid/expired token
  if (hasSession === false) {
    return (
      <div className="animate-slide-up text-center">
        <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-5">
          <AlertTriangle size={24} className="text-amber-500" />
        </div>
        <h1 className="text-2xl font-bold text-foreground mb-3">Link Expired</h1>
        <p className="text-sm text-muted-foreground mb-8 leading-relaxed max-w-xs mx-auto">
          This password reset link is invalid or has expired. Please request a new one.
        </p>
        <Link to="/forgot-password">
          <Button variant="primary" size="lg" id="request-new-reset-btn">
            Request New Link
          </Button>
        </Link>
      </div>
    );
  }

  // Success state
  if (success) {
    return (
      <div className="animate-slide-up text-center">
        <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-5">
          <CheckCircle2 size={24} className="text-emerald-500" />
        </div>
        <h1 className="text-2xl font-bold text-foreground mb-3">Password Updated</h1>
        <p className="text-sm text-muted-foreground mb-2 leading-relaxed">
          Your password has been changed successfully.
        </p>
        <p className="text-xs text-muted-foreground">Redirecting you to Sign In...</p>
      </div>
    );
  }

  return (
    <div className="animate-slide-up">
      {/* Header */}
      <div className="mb-8">
        <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-5">
          <KeyRound size={20} className="text-emerald-500" />
        </div>
        <h1 className="text-2xl font-bold text-foreground mb-2">Set New Password</h1>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Create a strong, new password for your CrimeLens AI account.
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <div>
          <Label htmlFor="new-password" required>New Password</Label>
          <PasswordInput
            id="new-password"
            placeholder="Create a new strong password"
            autoComplete="new-password"
            error={errors.password?.message}
            {...register('password')}
          />
          <PasswordStrengthIndicator password={watchedPassword} />
        </div>

        <div>
          <Label htmlFor="confirm-new-password" required>Confirm New Password</Label>
          <PasswordInput
            id="confirm-new-password"
            placeholder="Repeat your new password"
            autoComplete="new-password"
            error={errors.confirmPassword?.message}
            {...register('confirmPassword')}
          />
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          loading={isLoading}
          className="w-full mt-2"
          id="reset-password-submit-btn"
        >
          Update Password
        </Button>
      </form>
    </div>
  );
}

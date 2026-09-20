import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { PasswordInput } from '@/components/common/PasswordInput';
import { PasswordStrengthIndicator } from '@/components/common/PasswordStrengthIndicator';
import { GoogleButton } from '@/components/common/GoogleButton';


const signupSchema = z
  .object({
    fullName: z
      .string()
      .min(2, 'Full name must be at least 2 characters')
      .max(100, 'Name is too long')
      .regex(/^[a-zA-Z\s'-]+$/, 'Name can only contain letters, spaces, hyphens, and apostrophes'),
    email: z.string().email('Please enter a valid email address'),
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

type SignupFormData = z.infer<typeof signupSchema>;

export default function SignupPage() {
  const { signUp, signInWithGoogle } = useAuth();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema),
    mode: 'onChange',
  });

  const watchedPassword = watch('password', '');

  const onSubmit = async (data: SignupFormData) => {
    setIsLoading(true);
    try {
      await signUp({
        fullName: data.fullName,
        email: data.email,
        password: data.password,
        confirmPassword: data.confirmPassword,
      });
      toast.success('Account created! Check your email to verify your address.');
      navigate('/verify-email', { state: { email: data.email } });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Registration failed. Please try again.';
      toast.error(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogle = async () => {
    try {
      await signInWithGoogle();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Google sign in failed.';
      toast.error(msg);
    }
  };

  return (
    <div className="animate-slide-up">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground mb-2">Create Account</h1>
        <p className="text-sm text-muted-foreground">
          Join CrimeLens AI — request access from your agency administrator
        </p>
      </div>

      {/* Google OAuth */}
      <div className="mb-6">
        <GoogleButton onClick={handleGoogle} label="Sign up with Google" />
      </div>

      {/* Divider */}
      <div className="relative mb-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-border" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-background px-3 text-xs text-muted-foreground">or register with email</span>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <div>
          <Label htmlFor="signup-name" required>Full Name</Label>
          <Input
            id="signup-name"
            type="text"
            placeholder="John Smith"
            autoComplete="name"
            error={errors.fullName?.message}
            {...register('fullName')}
          />
        </div>

        <div>
          <Label htmlFor="signup-email" required>Email Address</Label>
          <Input
            id="signup-email"
            type="email"
            placeholder="officer@agency.gov"
            autoComplete="email"
            error={errors.email?.message}
            {...register('email')}
          />
        </div>

        <div>
          <Label htmlFor="signup-password" required>Password</Label>
          <PasswordInput
            id="signup-password"
            placeholder="Create a strong password"
            autoComplete="new-password"
            error={errors.password?.message}
            {...register('password')}
          />
          <PasswordStrengthIndicator password={watchedPassword} />
        </div>

        <div>
          <Label htmlFor="signup-confirm" required>Confirm Password</Label>
          <PasswordInput
            id="signup-confirm"
            placeholder="Repeat your password"
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
          id="signup-submit-btn"
        >
          Create Account
        </Button>
      </form>

      {/* Login link */}
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already have an account?{' '}
        <Link
          to="/login"
          className="font-medium text-emerald-500 hover:text-emerald-400 transition-colors"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}

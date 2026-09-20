import { cn } from '@/lib/utils';
import type { PasswordStrength, PasswordStrengthResult } from '@/types/auth';

interface PasswordStrengthIndicatorProps {
  password: string;
}

export function evaluatePasswordStrength(password: string): PasswordStrengthResult {
  if (!password) {
    return { strength: 'weak', score: 0, label: '', color: '' };
  }

  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[a-z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  // Normalize to 0-4
  const normalized = Math.min(4, Math.floor(score * (4 / 6)));

  const map: Record<number, { strength: PasswordStrength; label: string; color: string }> = {
    0: { strength: 'weak', label: 'Too weak', color: 'bg-red-500' },
    1: { strength: 'weak', label: 'Weak', color: 'bg-red-500' },
    2: { strength: 'fair', label: 'Fair', color: 'bg-amber-500' },
    3: { strength: 'good', label: 'Good', color: 'bg-emerald-400' },
    4: { strength: 'strong', label: 'Strong', color: 'bg-emerald-500' },
  };

  return { ...map[normalized], score: normalized };
}

export function PasswordStrengthIndicator({ password }: PasswordStrengthIndicatorProps) {
  const result = evaluatePasswordStrength(password);

  if (!password) return null;

  const segments = [0, 1, 2, 3];
  const requirements = [
    { label: 'At least 8 characters', met: password.length >= 8 },
    { label: 'Uppercase letter', met: /[A-Z]/.test(password) },
    { label: 'Lowercase letter', met: /[a-z]/.test(password) },
    { label: 'Number', met: /\d/.test(password) },
    { label: 'Special character', met: /[^A-Za-z0-9]/.test(password) },
  ];

  return (
    <div className="mt-2 space-y-2">
      {/* Strength bar */}
      <div className="flex items-center gap-1.5">
        {segments.map((i) => (
          <div
            key={i}
            className={cn(
              'h-1 flex-1 rounded-full transition-all duration-300',
              i < result.score ? result.color : 'bg-border'
            )}
          />
        ))}
        {result.label && (
          <span className={cn(
            'text-xs font-medium ml-1 shrink-0',
            result.score <= 1 && 'text-red-400',
            result.score === 2 && 'text-amber-400',
            result.score >= 3 && 'text-emerald-400',
          )}>
            {result.label}
          </span>
        )}
      </div>

      {/* Requirements */}
      <div className="grid grid-cols-1 gap-1">
        {requirements.map((req) => (
          <div key={req.label} className="flex items-center gap-2">
            <div className={cn(
              'w-1.5 h-1.5 rounded-full shrink-0 transition-colors duration-200',
              req.met ? 'bg-emerald-500' : 'bg-border'
            )} />
            <span className={cn(
              'text-xs transition-colors duration-200',
              req.met ? 'text-emerald-400' : 'text-muted-foreground'
            )}>
              {req.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

import { ScanEye } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Link } from 'react-router-dom';

interface LogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  to?: string;
}

const sizes = {
  sm: { icon: 16, text: 'text-base', container: 'gap-2' },
  md: { icon: 20, text: 'text-lg', container: 'gap-2.5' },
  lg: { icon: 24, text: 'text-xl', container: 'gap-3' },
};

export function Logo({ className, size = 'md', showText = true, to = '/' }: LogoProps) {
  const s = sizes[size];

  const content = (
    <div className={cn('flex items-center', s.container, className)}>
      <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
        <ScanEye size={s.icon} className="text-emerald-500" />
      </div>
      {showText && (
        <span className={cn('font-bold tracking-tight text-foreground', s.text)}>
          CrimeLens <span className="text-emerald-500">AI</span>
        </span>
      )}
    </div>
  );

  if (to) {
    return <Link to={to} className="inline-flex">{content}</Link>;
  }

  return content;
}

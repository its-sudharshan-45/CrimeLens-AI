import { Link, Outlet, useNavigate } from 'react-router-dom';
import { LogOut, User } from 'lucide-react';
import { toast } from 'sonner';

import { useAuth } from '@/hooks/useAuth';
import { Logo } from '@/components/common/Logo';

export default function DashboardLayout() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const handleSignOut = async () => {
    try {
      await signOut();
      toast.success('Signed out successfully');
      navigate('/login');
    } catch {
      toast.error('Failed to sign out');
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-4">
            <Link to="/dashboard" aria-label="CrimeLens AI dashboard">
              <Logo size="md" />
            </Link>
            <span className="hidden h-5 w-px bg-border sm:block" aria-hidden="true" />
            <span className="hidden truncate text-xs font-medium text-muted-foreground sm:block">
              Crime Risk Prediction
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 sm:flex">
              <div className="flex h-7 w-7 items-center justify-center rounded-full border border-border bg-secondary">
                <User size={13} className="text-muted-foreground" />
              </div>
              <span className="max-w-[180px] truncate text-xs text-muted-foreground">
                {user?.full_name || user?.email || 'User'}
              </span>
            </div>
            <button
              type="button"
              onClick={handleSignOut}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border px-2.5 text-xs font-medium text-muted-foreground transition-colors hover:border-red-500/30 hover:text-red-400"
              id="signout-btn"
            >
              <LogOut size={13} />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 sm:py-8">
        <Outlet />
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-1 px-4 py-4 text-[11px] text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <span>CrimeLens AI · Deep learning–based district crime risk prediction</span>
          <span>Decision-support only · Not for individual profiling</span>
        </div>
      </footer>
    </div>
  );
}

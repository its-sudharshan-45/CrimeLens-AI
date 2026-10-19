import { Link, Outlet } from 'react-router-dom';
import { Logo } from '@/components/common/Logo';

export default function AuthLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="flex justify-center px-6 py-6">
        <Link to="/" aria-label="CrimeLens AI home">
          <Logo size="lg" />
        </Link>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 pb-10 sm:px-6">
        <div className="w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl sm:p-8">
          <Outlet />
        </div>
      </main>

      <footer className="px-4 pb-6 text-center text-[11px] text-muted-foreground">
        CrimeLens AI · District crime risk prediction · Decision-support only
      </footer>
    </div>
  );
}

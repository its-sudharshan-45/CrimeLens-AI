import { useState, useEffect, useRef } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Logo } from '@/components/common/Logo';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import {
  LayoutDashboard,
  FileText,
  Tag,
  MapPin,
  FolderOpen,
  Search as SearchFiles,
  Brain,
  BarChart3,
  LogOut,
  User,
  ChevronRight,
  ChevronLeft,
  Menu,
  Shield,
  Home,
  ShieldCheck,
  HeartPulse,
  Database,
} from 'lucide-react';

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard',            href: '/dashboard',                  group: 'main' },
  { icon: FileText,        label: 'Crime Reports',        href: '/dashboard/reports',           group: 'main' },
  { icon: SearchFiles,     label: 'Investigations',       href: '/dashboard/investigations',    group: 'main' },
  { icon: FolderOpen,      label: 'Evidence',             href: '/dashboard/evidence',          group: 'main' },
  { icon: MapPin,          label: 'Crime Locations',      href: '/dashboard/locations',         group: 'main' },
  { icon: Tag,             label: 'Crime Categories',     href: '/dashboard/categories',        group: 'main' },
  { icon: Brain,           label: 'AI Prediction',        href: '/dashboard/ai',                group: 'ai' },
  { icon: BarChart3,       label: 'Analytics',            href: '/dashboard/analytics',         group: 'ai' },
  { icon: Shield,          label: 'Security',             href: '/dashboard/security',          group: 'admin' },
  { icon: ShieldCheck,     label: 'Audit Logs',            href: '/dashboard/audit-center',      group: 'admin' },
  { icon: HeartPulse,      label: 'System Health',         href: '/dashboard/system-health',     group: 'admin' },
  { icon: Database,        label: 'Backup & Recovery',     href: '/dashboard/backups',           group: 'admin' },
];

const groupLabels: Record<string, string> = {
  main: 'Crime Operations',
  ai: 'Intelligence',
  admin: 'Administration',
};

function getRouteLabel(pathname: string): { breadcrumbs: string[] } {
  const found = navItems.find((n) => n.href === pathname);
  if (found) return { breadcrumbs: ['CrimeLens AI', found.label] };
  return { breadcrumbs: ['CrimeLens AI'] };
}

const SIDEBAR_KEY = 'cl-sidebar-collapsed';

export default function DashboardLayout() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(SIDEBAR_KEY) === 'true'; } catch { return false; }
  });
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Persist collapsed state
  useEffect(() => {
    try { localStorage.setItem(SIDEBAR_KEY, String(collapsed)); } catch { /* */ }
  }, [collapsed]);

  // Close mobile sidebar on route change
  useEffect(() => { setMobileOpen(false); }, [location.pathname]);

  // Close user menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSignOut = async () => {
    try {
      await signOut();
      toast.success('Signed out successfully');
      navigate('/login');
    } catch {
      toast.error('Failed to sign out');
    }
  };

  const { breadcrumbs } = getRouteLabel(location.pathname);

  const groups = [...new Set(navItems.map((n) => n.group))];

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className={cn('flex items-center border-b border-border shrink-0', collapsed ? 'p-4 justify-center' : 'px-5 py-4')}>
        {collapsed ? (
          <Shield size={22} className="text-emerald-500" />
        ) : (
          <Logo size="md" to="/dashboard" />
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 space-y-4" aria-label="Main navigation">
        {groups.map((group) => {
          const items = navItems.filter((n) => n.group === group);
          return (
            <div key={group}>
              {!collapsed && (
                <p className="px-4 mb-1 text-[10px] font-semibold text-muted-foreground/50 uppercase tracking-widest">
                  {groupLabels[group]}
                </p>
              )}
              <div className="space-y-0.5 px-2">
                {items.map((item) => {
                  const isActive = location.pathname === item.href ||
                    (item.href !== '/dashboard' && location.pathname.startsWith(item.href));
                  return (
                    <Link
                      key={item.href}
                      to={item.href}
                      title={collapsed ? item.label : undefined}
                      className={cn(
                        'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 group relative',
                        collapsed ? 'justify-center' : '',
                        isActive
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/15'
                          : 'text-muted-foreground hover:text-foreground hover:bg-secondary border border-transparent',
                      )}
                    >
                      <item.icon
                        size={16}
                        className={cn('shrink-0', isActive ? 'text-emerald-500' : 'group-hover:text-foreground')}
                      />
                      {!collapsed && (
                        <>
                          <span className="flex-1">{item.label}</span>
                          {isActive && <ChevronRight size={12} className="text-emerald-500/50" />}
                        </>
                      )}
                    </Link>
                  );
                })}
              </div>
            </div>
          );
        })}
      </nav>

      {/* User footer */}
      <div className="shrink-0 p-2 border-t border-border">
        <div className={cn(
          'flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-secondary/40 mb-1.5',
          collapsed && 'justify-center',
        )}>
          <div className="w-7 h-7 rounded-full bg-emerald-500/20 border border-emerald-500/20 flex items-center justify-center shrink-0">
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt="avatar" className="w-full h-full rounded-full object-cover" />
            ) : (
              <User size={13} className="text-emerald-400" />
            )}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-foreground truncate">{user?.full_name || 'User'}</p>
              <p className="text-[10px] text-muted-foreground truncate">{user?.email}</p>
            </div>
          )}
        </div>
        <button
          onClick={handleSignOut}
          title={collapsed ? 'Sign Out' : undefined}
          className={cn(
            'flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-red-400 hover:bg-red-500/5 transition-colors duration-150',
            collapsed && 'justify-center',
          )}
          id="signout-btn"
        >
          <LogOut size={14} />
          {!collapsed && 'Sign Out'}
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* ── Desktop Sidebar ─────────────────────────────────────────── */}
      <aside
        className={cn(
          'hidden md:flex flex-col border-r border-border bg-card transition-all duration-300 ease-in-out shrink-0',
          collapsed ? 'w-[68px]' : 'w-[240px]',
        )}
      >
        <SidebarContent />
      </aside>

      {/* ── Mobile Sidebar Drawer ────────────────────────────────────── */}
      <>
        <div
          className={cn(
            'fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity duration-300 md:hidden',
            mobileOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none',
          )}
          onClick={() => setMobileOpen(false)}
        />
        <aside
          className={cn(
            'fixed top-0 left-0 z-50 h-full w-[240px] bg-card border-r border-border flex flex-col transition-transform duration-300 ease-out md:hidden',
            mobileOpen ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          <SidebarContent />
        </aside>
      </>

      {/* ── Main Content Area ────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Bar */}
        <header className="h-14 border-b border-border bg-card flex items-center justify-between px-4 md:px-6 shrink-0 gap-4">
          {/* Left: hamburger (mobile) + collapse button (desktop) + breadcrumbs */}
          <div className="flex items-center gap-3 min-w-0">
            {/* Mobile menu toggle */}
            <button
              className="md:hidden text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation"
            >
              <Menu size={18} />
            </button>

            {/* Desktop collapse toggle */}
            <button
              className="hidden md:flex items-center justify-center w-7 h-7 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
              onClick={() => setCollapsed((c) => !c)}
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>

            {/* Breadcrumbs */}
            <nav className="hidden md:flex items-center gap-1.5 text-sm min-w-0" aria-label="Breadcrumb">
              <Home size={12} className="text-muted-foreground shrink-0" />
              {breadcrumbs.map((crumb, i) => (
                <span key={i} className="flex items-center gap-1.5 min-w-0">
                  {i > 0 && <ChevronRight size={10} className="text-muted-foreground/40 shrink-0" />}
                  <span
                    className={cn(
                      'truncate',
                      i === breadcrumbs.length - 1
                        ? 'text-foreground font-medium'
                        : 'text-muted-foreground',
                    )}
                  >
                    {crumb}
                  </span>
                </span>
              ))}
            </nav>
          </div>

          {/* Right: live indicator + user */}
          <div className="flex items-center gap-3 shrink-0">
            {/* Live pulse */}
            <div className="hidden sm:flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[11px] text-muted-foreground font-medium">Live</span>
            </div>

            {/* User menu */}
            <div ref={userMenuRef} className="relative">
              <button
                onClick={() => setUserMenuOpen((o) => !o)}
                className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-secondary transition-colors"
                id="user-menu-btn"
                aria-expanded={userMenuOpen}
                aria-haspopup="true"
              >
                <div className="w-7 h-7 rounded-full bg-emerald-500/20 border border-emerald-500/20 flex items-center justify-center">
                  {user?.avatar_url ? (
                    <img src={user.avatar_url} alt="avatar" className="w-full h-full rounded-full object-cover" />
                  ) : (
                    <User size={12} className="text-emerald-400" />
                  )}
                </div>
                <span className="hidden sm:block text-xs font-medium text-foreground max-w-[100px] truncate">
                  {user?.full_name || user?.email?.split('@')[0] || 'User'}
                </span>
                <ChevronRight
                  size={12}
                  className={cn('text-muted-foreground transition-transform', userMenuOpen && 'rotate-90')}
                />
              </button>

              {/* Dropdown */}
              {userMenuOpen && (
                <div className="absolute top-full right-0 mt-1.5 w-52 bg-card border border-border rounded-xl shadow-card-lg z-50 overflow-hidden animate-slide-up">
                  <div className="px-4 py-3 border-b border-border">
                    <p className="text-sm font-medium text-foreground truncate">{user?.full_name || 'User'}</p>
                    <p className="text-[11px] text-muted-foreground truncate">{user?.email}</p>
                  </div>
                  <div className="py-1">
                    <button
                      onClick={() => { setUserMenuOpen(false); handleSignOut(); }}
                      className="flex items-center gap-2.5 w-full px-4 py-2 text-sm text-red-400 hover:bg-red-500/5 transition-colors"
                    >
                      <LogOut size={13} />Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';

// Providers
import { AuthProvider } from '@/contexts/AuthContext';

// Route guards
import { ProtectedRoute } from '@/routes/ProtectedRoute';
import { PublicRoute } from '@/routes/PublicRoute';

// Layouts
import AuthLayout from '@/layouts/AuthLayout';
import DashboardLayout from '@/layouts/DashboardLayout';

// Eagerly loaded critical pages
import LandingPage from '@/pages/LandingPage';
import NotFoundPage from '@/pages/NotFoundPage';

// Lazy loaded auth pages
const LoginPage = lazy(() => import('@/pages/auth/LoginPage'));
const SignupPage = lazy(() => import('@/pages/auth/SignupPage'));
const ForgotPasswordPage = lazy(() => import('@/pages/auth/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('@/pages/auth/ResetPasswordPage'));
const EmailVerificationPage = lazy(() => import('@/pages/auth/EmailVerificationPage'));

// Lazy loaded dashboard pages
const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'));
const CrimeReportsPage = lazy(() => import('@/pages/dashboard/CrimeReportsPage'));
const CrimeCategoriesPage = lazy(() => import('@/pages/dashboard/CrimeCategoriesPage'));
const CrimeLocationsPage = lazy(() => import('@/pages/dashboard/CrimeLocationsPage'));
const EvidencePage = lazy(() => import('@/pages/dashboard/EvidencePage'));
const InvestigationsPage = lazy(() => import('@/pages/dashboard/InvestigationsPage'));
const AIPredictionsPage = lazy(() => import('@/pages/dashboard/AIPredictionsPage'));
const AnalyticsPage = lazy(() => import('@/pages/dashboard/AnalyticsPage'));
const AuditCenterPage = lazy(() => import('@/pages/dashboard/AuditCenterPage'));
const SecurityDashboardPage = lazy(() => import('@/pages/dashboard/SecurityDashboardPage'));
const SystemHealthPage = lazy(() => import('@/pages/dashboard/SystemHealthPage'));
const BackupRecoveryPage = lazy(() => import('@/pages/dashboard/BackupRecoveryPage'));

// Lazy loaded error pages
const ForbiddenPage = lazy(() => import('@/pages/errors/ForbiddenPage'));
const ErrorPage = lazy(() => import('@/pages/errors/ErrorPage'));

// Suspense fallback spinner
function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[400px] w-full">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs text-muted-foreground font-medium">Loading module...</span>
      </div>
    </div>
  );
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <AuthProvider>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              {/* Public landing */}
              <Route path="/" element={<LandingPage />} />

              {/* Email verification (accessible to logged in & logged out) */}
              <Route path="/verify-email" element={<AuthLayout />}>
                <Route index element={<EmailVerificationPage />} />
              </Route>

              {/* Reset password (accessed via Supabase email link) */}
              <Route path="/reset-password" element={<AuthLayout />}>
                <Route index element={<ResetPasswordPage />} />
              </Route>

              {/* Public auth routes (redirect if already logged in) */}
              <Route element={<PublicRoute />}>
                <Route element={<AuthLayout />}>
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/signup" element={<SignupPage />} />
                  <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                </Route>
              </Route>

              {/* Protected dashboard routes */}
              <Route element={<ProtectedRoute />}>
                <Route element={<DashboardLayout />}>
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/dashboard/reports" element={<CrimeReportsPage />} />
                  <Route path="/dashboard/categories" element={<CrimeCategoriesPage />} />
                  <Route path="/dashboard/locations" element={<CrimeLocationsPage />} />
                  <Route path="/dashboard/evidence" element={<EvidencePage />} />
                  <Route path="/dashboard/investigations" element={<InvestigationsPage />} />
                  <Route path="/dashboard/ai" element={<AIPredictionsPage />} />
                  <Route path="/dashboard/analytics" element={<AnalyticsPage />} />
                  <Route path="/dashboard/audit-center" element={<AuditCenterPage />} />
                  <Route path="/dashboard/security" element={<SecurityDashboardPage />} />
                  <Route path="/dashboard/system-health" element={<SystemHealthPage />} />
                  <Route path="/dashboard/backups" element={<BackupRecoveryPage />} />
                </Route>
              </Route>

              {/* Error routes */}
              <Route path="/403" element={<ForbiddenPage />} />
              <Route path="/500" element={<ErrorPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Suspense>

          {/* Global toast notifications */}
          <Toaster
            position="top-right"
            richColors={false}
            toastOptions={{
              duration: 4000,
              style: {
                fontFamily: 'Inter, sans-serif',
                fontSize: '13px',
              },
            }}
          />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;

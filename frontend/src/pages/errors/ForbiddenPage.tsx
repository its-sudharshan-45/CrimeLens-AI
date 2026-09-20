import { Link } from 'react-router-dom';
import { ShieldAlert, Home, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function ForbiddenPage() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="text-center max-w-md animate-slide-up">
        <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-6">
          <ShieldAlert size={28} className="text-red-400" />
        </div>

        <h1 className="text-7xl font-bold text-foreground/10 mb-2">403</h1>
        <h2 className="text-xl font-semibold text-foreground mb-3">Access Denied</h2>
        <p className="text-sm text-muted-foreground mb-8 leading-relaxed">
          You do not have permission to view this resource. Please verify your authentication credentials or return to the dashboard.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link to="/dashboard">
            <Button variant="primary" size="md" className="gap-2 w-full sm:w-auto">
              <Home size={15} />
              Return to Dashboard
            </Button>
          </Link>
          <button
            onClick={() => window.history.back()}
            className="inline-flex items-center justify-center gap-2 h-10 px-4 text-sm font-medium text-muted-foreground hover:text-foreground border border-border rounded-lg transition-all duration-150"
          >
            <ArrowLeft size={15} />
            Go Back
          </button>
        </div>
      </div>
    </div>
  );
}

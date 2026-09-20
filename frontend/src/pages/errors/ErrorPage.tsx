import { Link } from 'react-router-dom';
import { ServerCrash, RefreshCw, Home } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function ErrorPage() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="text-center max-w-md animate-slide-up">
        <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-6">
          <ServerCrash size={28} className="text-amber-400" />
        </div>

        <h1 className="text-7xl font-bold text-foreground/10 mb-2">500</h1>
        <h2 className="text-xl font-semibold text-foreground mb-3">System Error</h2>
        <p className="text-sm text-muted-foreground mb-8 leading-relaxed">
          An unexpected server error or network issue occurred. Our automated error monitoring has recorded this event.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button
            variant="primary"
            size="md"
            className="gap-2 w-full sm:w-auto"
            onClick={() => window.location.reload()}
          >
            <RefreshCw size={15} />
            Reload Page
          </Button>
          <Link to="/dashboard">
            <button className="inline-flex items-center justify-center gap-2 h-10 px-4 text-sm font-medium text-muted-foreground hover:text-foreground border border-border rounded-lg transition-all duration-150 w-full sm:w-auto">
              <Home size={15} />
              Go to Dashboard
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
}
